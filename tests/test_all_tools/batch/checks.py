"""Batch edits: apply_edits, and the rollback of a call that fails after it changed something (server_tools/core.py,
_with_undo; mcp_server/designer_rollback.py), with the Designer facts it relies on."""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Literal

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

from test_all_tools import common
from test_all_tools.batch.failed_calls import ERROR, call_text, compared, during_rollback, rolled_back
from test_all_tools.common import (
    GRAPH_OF,
    ROLLED_BACK,
    TEST_GRAPH,
    Ctx,
    ToolArgs,
    added_id,
    cancel_from_second_client,
    check,
    described,
    designer_script,
    graph_in_editor,
    own_step,
    positions,
    script_path,
    sd_run,
    skip,
    text,
    until_job_running,
)

# s at most for the scripts run with sd_run: above their rollback's own limit of 60 s, so that one waiting it out
# still reports (REVIEW.md TST-845)
SCRIPT_S = 2 * 60 + 10
# code that adds a node to the self-test graph: a change for a failing call to take back
NEW_NODE = "g.newNode('sbs::compositing::uniform')\n"  # one node added to the graph `g`
ADD = GRAPH_OF % TEST_GRAPH + NEW_NODE
# code that runs until its timeout or a cancel
LOOP = dedent("""\
    while True:
        pass
""")
# code that ends with sys.exit(<a code>)
EXIT = dedent("""\
    import sys
    sys.exit(%d)""")
# a job that says whether it runs inside the rollback of another: its frames among the ones it was called from
NESTED = dedent("""\
    import traceback
    print('NESTED=%s' % ('roll_back' in [frame.name for frame in traceback.extract_stack()]))""")
# commits the transaction a call left open, as the transaction a call's step is
COMMIT = 'from sd.api.sdhistoryutils import SDHistoryUtils; SDHistoryUtils.commitTransaction()'
# the count of Designer's open user packages
PACKAGES = "import sd; print('PACKAGES=%d' % len(sd.getContext().getSDApplication().getPackageMgr().getUserPackages()))"
# how a failed batch's error tells the agent to undo what stays applied (designer_helpers/batch.py, the KEPT line)
TAKE_BACK = 'undo_edits takes back the whole batch'


def said_step() -> str:
    """The pattern of a step's name as undo_edits says it, the call's label as its group, then the tag
    (project_constants.py, new_tag): built from the tag's constants as they are, which a unit test switches to the
    invisible form (REVIEW.md SRV-271)."""
    return r"'(Claude: [^'#]+)" + own_step('') + "'"


SAID_STEP = said_step()
# the mark after a read's step in undo_edits' reply, or none: with SAID_STEP, a step's label and its mark
READ_SAID = " (a read of this session's: it changed nothing)"
READ_MARK = '(%s)?' % re.escape(READ_SAID)
# keeps the self-test graph where TIMED_OUT finds it, as CURRENT_GRAPH keeps the user's
BIND_GRAPH = GRAPH_OF % TEST_GRAPH + 'import sys; sys._selftest_timed_graph = g\n'
UNBIND_GRAPH = "import sys; sys.__dict__.pop('_selftest_timed_graph', None)"
# code that adds a node, printing its id, then outlasts a timeout_s of 1 in one C call, the first %s before that call
# and the second after it (check_a_timeout_never_leaves_a_calls_step_open)
TIMED_OUT = dedent("""\
    import sys, time
    print('ADDED=' + sys._selftest_timed_graph.newNode('sbs::compositing::uniform').getIdentifier())
    %stime.sleep(1)
    %s""")
SLEEP_LINE = TIMED_OUT.partition('time.sleep')[0].count('\n') + 1  # the C call's line, with no statements before it
TRACED_EVERY = 64  # the plugin's tracer looks at the time at every 64th traced event (_make_tracer)
# the traced events after the code that the calls' abort is aimed at: on the template before the fix (REVIEW.md
# SRV-273), the template's with line at 1, UndoGroup.__exit__ at 3, SDHistoryUtils.commitTransaction at 5,
# sd.getContext at 7 and its import at 9, each before the C commit. With sd's public commitTransaction left traced (the
# template of SRV-276 with its settrace(None) removed), each of the five left the step open too (measured 2026-11-25)
TIMED_AFTER = (1, 3, 5, 7, 9)
# code that makes more steps than Designer's Undo dropdown lists (25), each a node added outside any undo group
BURY = GRAPH_OF % TEST_GRAPH + NEW_NODE * 30


async def run(ctx: Ctx) -> None:
    c, G, slope, lv = ctx.c, ctx.G, ctx.slope, ctx.lv
    # --- batch edits
    t = text(
        await c(
            'apply_edits',
            {
                'ops': [
                    {
                        'op': 'add',
                        'definition': 'uniform',
                        'ref': 'u',
                        'position': [-300, 300],
                        'params': {'colorswitch': False, 'outputcolor': [0.5, 0.5, 0.5, 1]},
                    },
                    {'op': 'add', 'definition': 'blend', 'ref': 'b', 'params': {'blendingmode': 'multiply'}},
                    {'op': 'connect', 'from': 'u', 'to': 'b', 'input': 'source'},
                    {'op': 'connect', 'from': slope, 'to': 'b', 'input': 'destination'},
                    {'op': 'move', 'node': 'b', 'position': [0, 300]},
                    {'op': 'set', 'node': 'b', 'params': {'opacitymult': 0.5}},
                    {'op': 'disconnect', 'node': 'b', 'input': 'destination'},
                    {
                        'op': 'expose',
                        'node': 'b',
                        'param': 'opacitymult',
                        'input_id': 'batch_opacity',
                        'max': 1,
                        'step': 0.05,
                        'group': 'Batch',
                    },
                ],
                **G,
            },
        )
    )
    check(
        'apply_edits',
        '8 ops with refs',
        'applied 8 op(s)' in t and 'removed 1 connection(s) into' in t and "graph input 'batch_opacity'" in t,
        t.splitlines()[-1],
    )
    line = next((l for l in text(await c('list_graph_inputs', G)).splitlines() if l.startswith('batch_opacity')), '')
    check('apply_edits', 'expose op passes step and group', "group='Batch'" in line and 'step=0.05' in line, line)
    await c('remove_graph_input', {'input_id': 'batch_opacity', **G})
    # no match raises AttributeError, which the run's except reports (REVIEW.md TST-63)
    batch_blend = re.search(r"'b': '(\d+)'", t).group(1)  # type: ignore[union-attr]
    await check_a_batch_failing_after_adds_and_connects_is_rolled_back(ctx)
    await check_nothing_is_undone_when_nothing_changed(ctx)
    # positions as numeric strings work, as main's float() conversion allowed (REVIEW.md HLP-50)
    t = text(
        await c(
            'apply_edits',
            {'ops': [{'op': 'add', 'definition': 'blur', 'ref': 's', 'position': ['100', '-200.5']}], **G},
        )
    )
    string_pos = re.search(r"'s': '(\d+)'", t)
    try:
        check('apply_edits', 'add: a position as numeric strings', 'added' in t and '@(100,-200)' in t, t.strip()[:120])
    finally:
        if string_pos:
            await c('apply_edits', {'ops': [{'op': 'delete', 'node': string_pos.group(1)}], **G})
    # the "its node was added" note only when a node really was (REVIEW.md HLP-5)
    r_ = await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'not_a_real_node', 'params': {'a': 1}}], **G})
    check(
        'apply_edits',
        'a bad definition is not reported as added',
        r_.is_error and 'op 0 (add) failed' in text(r_) and 'its node was added' not in text(r_),
        text(r_),
    )
    # an add whose params fail now leaves no node at all, and says so (REVIEW.md HLP-30)
    before = text(await designer_script(c, 'shared/count_nodes', graph=TEST_GRAPH))
    r_ = await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels', 'params': {'nope': 1}}], **G})
    after = text(await designer_script(c, 'shared/count_nodes', graph=TEST_GRAPH))
    check(
        'apply_edits',
        'an add whose params failed leaves no node, and says so',
        r_.is_error and 'not added' in text(r_) and 'its node was added' not in text(r_) and before == after,
        text(r_),
    )
    # a ref reused after its first node is deleted names the new node: the pre-check's tracking of
    # deleted nodes (REVIEW.md HLP-42) doesn't refuse it
    r_ = await c(
        'apply_edits',
        {
            'ops': [
                {'op': 'add', 'definition': 'blur', 'ref': 'r', 'position': [900, 900]},
                {'op': 'delete', 'node': 'r'},
                {'op': 'add', 'definition': 'blur', 'ref': 'r', 'position': [900, 900]},
                {'op': 'move', 'node': 'r', 'position': [950, 900]},
                {'op': 'delete', 'node': 'r'},
            ],
            **G,
        },
    )
    check(
        'apply_edits', 'a ref reused after a delete names the new node', 'applied 5 op(s)' in text(r_), text(r_)[-150:]
    )
    # an enum value as a numeric string, like int parameters accept (REVIEW.md HLP-11)
    r_ = await c('apply_edits', {'ops': [{'op': 'set', 'node': batch_blend, 'params': {'blendingmode': '3'}}], **G})
    check('apply_edits', 'set: enum value as a numeric string', not r_.is_error, text(r_))
    t = text(await c('describe_graph', G))
    x_ids = [l.split()[0] for l in t.splitlines() if ' levels ' in l and l.split()[0] != lv]
    await c(
        'apply_edits',
        {
            'ops': [
                {'op': 'delete', 'node': n}
                for n in x_ids + [batch_blend] + [l.split()[0] for l in t.splitlines() if ' uniform ' in l]
            ],
            **G,
        },
    )
    # a field the op doesn't take refuses the whole batch: a typo reported success, the node somewhere else and its
    # parameters unset (REVIEW.md HLP-62)
    before = text(await designer_script(c, 'shared/count_nodes', graph=TEST_GRAPH))
    r_ = await c(
        'apply_edits',
        {
            'ops': [
                {'op': 'add', 'definition': 'levels'},
                {'op': 'add', 'definition': 'levels', 'postion': [999, 999]},
            ],
            **G,
        },
    )
    after = text(await designer_script(c, 'shared/count_nodes', graph=TEST_GRAPH))
    check(
        'apply_edits',
        'refuses a field the op does not take, nothing added',
        r_.is_error and "unknown field 'postion'" in text(r_) and 'position' in text(r_) and after == before,
        text(r_)[-200:],
    )
    await check_a_step_after_a_calls_own_is_left_alone(ctx)
    await check_one_history_for_every_package_each_step_shown_as_it_commits(ctx)
    await check_a_rollback_leaves_a_saved_package_marked_modified(ctx)
    await check_a_graph_whose_save_fails_leaves_no_package(ctx)
    await check_a_sweep_failing_on_its_output_is_rolled_back(ctx)
    await check_a_code_tools_failure_after_a_change_is_rolled_back(ctx)
    await check_a_cancel_during_a_rollback_leaves_it_to_finish(ctx)
    await check_a_job_queued_during_a_rollback_runs_after_it(ctx)
    await check_a_script_ending_with_sys_exit(ctx)
    await check_undo_edits_takes_back_the_sessions_last_calls(ctx)
    await check_undo_edits_takes_back_a_step_redone(ctx)
    await check_undo_edits_names_another_clients_step_on_top_until_include_others(ctx)
    await check_undo_edits_takes_a_reads_step_along_uncounted(ctx)
    await check_undo_edits_takes_describe_nodes_steps_along_uncounted(ctx)
    await check_undo_edits_takes_search_nodes_scan_along_uncounted(ctx)
    await check_undo_edits_refuses_calls_beyond_the_steps_listed(ctx)
    await check_the_undo_list_shows_the_newest_steps_only(ctx)
    await check_a_timeout_never_leaves_a_calls_step_open(ctx)


async def check_a_batch_failing_after_adds_and_connects_is_rolled_back(ctx: Ctx) -> None:
    """A batch that fails after it added nodes, connected them, set a parameter and exposed one is rolled back whole:
    the graph and its inputs are as before, and the error says its step was taken back, with no "were applied" and no
    advice to undo it with undo_edits. Before the rollback, the nodes stayed and the error named them (REVIEW.md SRV-35). A rollback that fails
    leaves the batch's nodes, input and value, which are taken out after (REVIEW.md TST-845)."""
    c, G = ctx.c, ctx.G
    before = await described(ctx) + text(await c('list_graph_inputs', G))
    after: str | None = None
    try:
        r_ = await c(
            'apply_edits',
            {
                'ops': [
                    {'op': 'add', 'definition': 'levels', 'ref': 'x', 'position': [0, 600]},
                    {'op': 'add', 'definition': 'blur', 'ref': 'y', 'position': [300, 600]},
                    {'op': 'connect', 'from': ctx.slope, 'to': 'x', 'input': 'input1'},
                    {'op': 'connect', 'from': 'x', 'to': 'y', 'input': 'input1'},
                    {'op': 'set', 'node': ctx.lv, 'params': {'levelinlow': [0.2, 0.2, 0.2, 0.2]}},
                    {'op': 'expose', 'node': 'y', 'param': 'intensity', 'input_id': 'rolled_back'},
                    {'op': 'connect', 'from': 'x', 'to': 'y', 'input': 'nope'},
                ],
                **G,
            },
        )
        after = await described(ctx) + text(await c('list_graph_inputs', G))
        t = text(r_)
        check(
            'apply_edits',
            'a batch failing after adds, connects, a set and an expose is rolled back, and says so',
            r_.is_error
            and 'op 6 (connect) failed' in t
            and ROLLED_BACK in t
            and 'were applied' not in t
            and TAKE_BACK not in t
            and after == before,
            t.strip()[-300:] + ('' if after == before else ' | the graph or its inputs changed'),
        )
    finally:
        if after != before:
            left = await described(ctx) + text(await c('list_graph_inputs', G))
            for node in sorted(set(positions(left)) - set(positions(before))):
                await c('apply_edits', {'ops': [{'op': 'delete', 'node': node}], **G})
            if 'rolled_back (' in left:
                await c('remove_graph_input', {'input_id': 'rolled_back', **G})
            await c(
                'apply_edits', {'ops': [{'op': 'set', 'node': ctx.lv, 'params': {'levelinlow': [0, 0, 0, 0]}}], **G}
            )


async def check_nothing_is_undone_when_nothing_changed(ctx: Ctx) -> None:
    """A batch whose first op fails as it runs, and one the pre-check refuses, change nothing, so nothing is undone:
    the step made before them stays (a sentinel node added), and neither error says a step was taken back or advises
    undo_edits, which would undo that step. The sentinel is deleted after."""
    c, G = ctx.c, ctx.G
    added = text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [600, 600]}], **G}))
    sentinel = added_id(added)
    try:
        failed = await c(
            'apply_edits', {'ops': [{'op': 'connect', 'from': ctx.lv, 'to': ctx.lv, 'input': 'nope'}], **G}
        )
        refused = await c(
            'apply_edits',
            {
                'ops': [
                    {'op': 'add', 'definition': 'blur', 'ref': 'r'},
                    {'op': 'connect', 'from': 'r', 'to': 'no_such_node', 'input': 'input1'},
                ],
                **G,
            },
        )
        stays = re.search(r'^%s blur ' % sentinel, text(await c('describe_graph', G)), re.M) is not None
        for name, r_, says in (
            ('its first op failing as it runs', failed, 'op 0 (connect) failed'),
            ('the pre-check refusing it', refused, 'nothing was applied'),
        ):
            t = text(r_)
            check(
                'apply_edits',
                'nothing undone after a batch that changed nothing: %s' % name,
                r_.is_error and says in t and ROLLED_BACK not in t and TAKE_BACK not in t and stays,
                t.strip()[-200:] + ('' if stays else ' | the step before it was undone'),
            )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': sentinel}], **G})


async def check_a_step_after_a_calls_own_is_left_alone(ctx: Ctx) -> None:
    """A step made after a failed call's own, before the rollback looks at the history: the rollback undoes nothing,
    saying the step on top isn't the call's (batch/designer_scripts/step_after_ours.py, run outside any undo group).
    The nodes both steps added are deleted after."""
    r = sd_run(script_path('batch/step_after_ours'), timeout=SCRIPT_S)
    found: dict[str, str] = dict(re.findall(r'^(STATE|ADDED|LEFT)=(.*)$', r.stdout, re.M))
    try:
        check(
            'rollback',
            "a step made after a failed call's own is left alone, and so is the call's",
            r.returncode == 0 and found.get('STATE', '').startswith('not ours: ') and found.get('LEFT') == '1 1',
            (r.stdout + r.stderr).strip()[-300:],
        )
    finally:
        # only the nodes still there, as LEFT says: one a broken rollback undid would make the batch refused (TST-845)
        pairs = zip(
            found.get('ADDED', '').split(), found.get('LEFT', '').split(), strict=False
        )  # none if it never got so far
        left = [n for n, there in pairs if there == '1']
        if left:
            await ctx.c('apply_edits', {'ops': [{'op': 'delete', 'node': n} for n in left], **ctx.G})


async def check_one_history_for_every_package_each_step_shown_as_it_commits(ctx: Ctx) -> None:
    """Designer's history, as the rollback reads it and waits on it (batch/designer_scripts/history_facts.py, run
    outside any undo group): a step in a graph of each of two packages, both listed in the one Undo dropdown, newest
    first, each on top as its undo group commits, before any event is processed, its name exactly as given, its tag
    included. Then the newest step is undone through the history manager's undo() slot, only while it is on top. The
    undo lands as Designer processes the events after the slot's call. It changes the dropdowns' actions, which wakes
    the rollback's own filter on them at least once before its wait's limit (REVIEW.md TST-842, TST-862, TST-864)."""
    r = sd_run(script_path('batch/history_facts'), timeout=SCRIPT_S)
    found: dict[str, str] = dict(re.findall(r'^(NAMES|AT_COMMIT|TOP_TWO|WOKEN)=(.*)$', r.stdout, re.M))
    names: list[str] | None = json.loads(found['NAMES']) if 'NAMES' in found else None
    said = (r.stdout + r.stderr).strip()[-300:]
    check(
        'designer facts',
        'one Undo history for the steps of two packages, newest first',
        r.returncode == 0 and names is not None and json.loads(found.get('TOP_TWO', 'null')) == names[::-1],
        said,
    )
    check(
        'designer facts',
        'a step is on top of the Undo dropdown as its group commits, its name and tag exact',
        r.returncode == 0 and names is not None and json.loads(found.get('AT_COMMIT', 'null')) == names,
        said,
    )
    woken: dict[str, object] = json.loads(found.get('WOKEN', '{}'))
    wakes = woken.get('wakes')
    check(
        'designer facts',
        "an undo of the newest step lands after the slot's call, waking the rollback's filter on the dropdowns before "
        "its wait's limit",
        names is not None
        and woken.get('called') is True
        and isinstance(wakes, int)
        and wakes >= 1
        and woken.get('limit_running') is True
        and woken.get('redo_top') == names[-1],
        said,
    )


async def check_a_rollback_leaves_a_saved_package_marked_modified(ctx: Ctx) -> None:
    """A batch failing on a graph just saved is rolled back to the graph as saved, and Designer still marks its package
    modified: what the error says of it (server_tools/core.py, UNDONE). On a graph of its own, saved in the category's
    folder."""
    c = ctx.c
    name = TEST_GRAPH + '_rollback_saved'
    G = {'graph': name}
    await c('create_graph', {'name': name, 'save_path': os.path.join(ctx.scratch, name + '.sbs'), 'size_log2': 4})
    r_ = await c(
        'apply_edits',
        {
            'ops': [
                {'op': 'add', 'definition': 'blur', 'ref': 'b'},
                {'op': 'connect', 'from': 'b', 'to': 'b', 'input': 'nope'},
            ],
            **G,
        },
    )
    diff = text(await c('diff_graph', {'against': 'saved', **G}))
    modified = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % name + "print('MODIFIED=%s' % g.getPackage().isModified())",
            },
        )
    )
    check(
        'designer facts',
        'a rollback on a saved package leaves its graph as saved and the package marked modified',
        r_.is_error and ROLLED_BACK in text(r_) and 'No differences' in diff and 'MODIFIED=True' in modified,
        text(r_).strip()[-150:] + ' | ' + diff.strip()[-100:] + ' | ' + modified.strip()[-60:],
    )


async def check_a_graph_whose_save_fails_leaves_no_package(ctx: Ctx) -> None:
    """create_graph whose save fails (its folder can't be made: a file is there) takes back the package it made: as many
    user packages are open after the call as before it, none holding the graph. Its error says its step was taken back
    (REVIEW.md TST-871)."""
    c = ctx.c
    name = TEST_GRAPH + '_failed_save'
    blocker = os.path.join(ctx.scratch, 'a_file')
    with open(blocker, 'w'):
        pass
    before = await call_text(ctx, 'execute_designer_code', {'code': PACKAGES})
    r_ = await c('create_graph', {'name': name, 'save_path': os.path.join(blocker, name + '.sbs'), 'size_log2': 4})
    after = await call_text(ctx, 'execute_designer_code', {'code': PACKAGES})
    found = await call_text(ctx, 'describe_graph', {'graph': name})
    check(
        'create_graph',
        'a save that fails leaves no package, and says so',
        r_.is_error
        and ROLLED_BACK in text(r_)
        and 'PACKAGES=' in before
        and before == after
        and 'not found in open user packages' in found,
        '%s -> %s | %s | %s' % (before.strip(), after.strip(), text(r_).strip()[-100:], found.strip()[-60:]),
    )


async def check_a_sweep_failing_on_its_output_is_rolled_back(ctx: Ctx) -> None:
    """sweep_param failing on an output its node doesn't have, after it set the first value, is rolled back, and its
    error says its step was taken back (the sweep puts its value back too, so only the error tells)."""
    sweep: ToolArgs = {'node_id': ctx.lv, 'param': 'levelinlow', 'values': [[0.2] * 4], 'output': 'nope', **ctx.G}
    await rolled_back(
        ctx,
        'sweep_param',
        'a sweep failing on a bad output is rolled back',
        [ERROR],
        lambda: call_text(ctx, 'sweep_param', sweep),
    )


async def check_a_code_tools_failure_after_a_change_is_rolled_back(ctx: Ctx) -> None:
    """The code tools' failures after a change, each rolled back, its error saying so: execute_designer_code
    whose code raises, is stopped by its timeout_s, or is cancelled by a second client (cancel_designer_job), and
    run_designer_script whose script raises."""
    E = 'execute_designer_code'
    script = os.path.join(ctx.scratch, 'fails_after_a_change.py')
    with open(script, 'w', encoding='utf-8') as f:
        f.write(ADD + "raise RuntimeError('the script failed')\n")

    async def cancelled() -> str:
        job = asyncio.create_task(call_text(ctx, E, {'code': ADD + LOOP, 'timeout_s': 60}))
        return await cancel_from_second_client() + '\n' + await job

    for name, says, call in (
        (
            'raising',
            ['ValueError: the code failed'],
            lambda: call_text(ctx, E, {'code': ADD + "raise ValueError('the code failed')"}),
        ),
        ('timing out', ['timed out'], lambda: call_text(ctx, E, {'code': ADD + LOOP, 'timeout_s': 1})),
        ('cancelled', ['running: True', 'cancelled by client'], cancelled),
    ):
        await rolled_back(ctx, E, 'code %s after a change is rolled back' % name, says, call)
    await rolled_back(
        ctx,
        'run_designer_script',
        'a script raising after a change is rolled back',
        ['RuntimeError: the script failed'],
        lambda: call_text(ctx, 'run_designer_script', {'path': script, 'timeout_s': 60}),
    )


async def check_a_cancel_during_a_rollback_leaves_it_to_finish(ctx: Ctx) -> None:
    """A second client's cancel_designer_job landing while a failed call's rollback runs leaves the rollback to finish,
    untraced: the graph as before, and the error is the call's own and says its step was taken back
    (batch/designer_scripts/during_rollback.py). Traced, the abort landed in the rollback, and nothing was undone
    (measured in Designer, 2026-11-24; test_plugin.py's test_an_abort_never_stops_a_rollback_halfway)."""
    await rolled_back(
        ctx,
        'rollback',
        "a cancel landing during a rollback leaves it to finish, and the call's own error",
        ['UNTRACED=True', 'CANCEL=cancel requested (running: True', 'RuntimeError: the script failed'],
        lambda: call_text(ctx, 'run_designer_script', during_rollback('cancel')),
    )


async def check_a_job_queued_during_a_rollback_runs_after_it(ctx: Ctx) -> None:
    """A second client's job queued while a failed call's rollback runs: it ran after the call, not inside the
    rollback's wait, and the call was rolled back (batch/designer_scripts/during_rollback.py). Whether the job would
    nest without the plugin's guard (`draining`, its _drain) isn't seen here: that guard's test is
    tests/unit/test_plugin.py::test_a_job_never_starts_inside_the_running_one (REVIEW.md TST-853)."""

    async def queued() -> str:
        job = asyncio.create_task(call_text(ctx, 'run_designer_script', during_rollback('queue')))
        await until_job_running(30)
        second = await asyncio.to_thread(sd_run, '-c', NESTED, timeout=SCRIPT_S)  # behind the rollback's limit
        return await job + '\n' + second.stdout + second.stderr

    await rolled_back(
        ctx,
        'rollback',
        'a job queued during a rollback runs after the call, which is rolled back',
        ['UNTRACED=True', '1 queued', 'RuntimeError: the script failed', 'NESTED=False'],
        queued,
    )


async def check_a_script_ending_with_sys_exit(ctx: Ctx) -> None:
    """Code ending with sys.exit(0) after a change ends normally: no error, the change kept (the node it added, deleted
    after). So does a script sd_run.py sends, which no undo group wraps: the plugin ends it normally. With sys.exit(1)
    the code fails: an error, and the change rolled back (the user, 2026-11-24)."""
    E = 'execute_designer_code'
    t, same = await compared(ctx, lambda: call_text(ctx, E, {'code': ADD + EXIT % 0}))
    check(
        E,
        'code ending with sys.exit(0) ends normally, its change kept',
        '--- ERROR ---' not in t and not same,
        ('the graph as before | ' if same else 'the graph changed | ') + (t.strip().splitlines() or [''])[-1],
    )
    r = await asyncio.to_thread(sd_run, '-c', EXIT % 0)
    check(
        'sd_run.py', 'a script ending with sys.exit(0) ends normally', r.returncode == 0, (r.stdout + r.stderr)[-150:]
    )
    await rolled_back(
        ctx,
        E,
        'code ending with sys.exit(1) fails, rolled back',
        ['SystemExit: 1'],
        lambda: call_text(ctx, E, {'code': ADD + EXIT % 1}),
    )


async def check_undo_edits_takes_back_the_sessions_last_calls(ctx: Ctx) -> None:
    """Three calls whose steps are named apart, then undo_edits(count=3): the graph as before them, and the reply names
    each call's step, newest first, with its tag, and says they are on Designer's Redo list (REVIEW.md TST-874: named
    alike, oldest first passed too). The nodes a failure leaves are deleted after."""
    c, G = ctx.c, ctx.G

    async def three_then_undone() -> str:
        await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [600, 900]}], **G})
        await c('execute_designer_code', {'code': ADD})
        await c(
            'apply_edits',
            {
                'ops': [
                    {'op': 'add', 'definition': 'blend', 'position': [900, 900]},
                    {'op': 'move', 'node': ctx.lv, 'position': [0, 0]},
                ],
                **G,
            },
        )
        r_ = await c('undo_edits', {'count': 3})
        return (ERROR if r_.is_error else '') + text(r_)

    t, same = await compared(ctx, three_then_undone)
    check(
        'undo_edits',
        "three calls taken back, the graph as before, each call's step named, newest first",
        not t.startswith(ERROR)
        and same
        and re.findall(SAID_STEP, t) == ['Claude: apply 2 edits', 'Claude: code', 'Claude: apply 1 edits']
        and 'Redo list' in t,
        ('' if same else 'the graph changed | ') + t.strip()[-300:],
    )


async def check_undo_edits_takes_back_a_step_redone(ctx: Ctx) -> None:
    """A call, undo_edits, then a Redo from code (batch/designer_scripts/redo_top.py, outside any undo group): the
    call's step tops the Undo list again, and undo_edits takes it back, named as the session's, unmarked (the user,
    2026-11-25). The graph is as before the call. The nodes a failure leaves are deleted after."""
    c, G = ctx.c, ctx.G
    redone: list[str] = []

    async def undone_redone_undone() -> str:
        await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [600, 1500]}], **G})
        await c('undo_edits', {})
        r = await asyncio.to_thread(sd_run, script_path('batch/redo_top'), timeout=SCRIPT_S)
        found = re.search(r'^REDONE=(.*)$', r.stdout, re.M)
        if not found:
            return ERROR + 'the Redo: ' + (r.stdout + r.stderr).strip()[-200:]
        redone.append(json.loads(found.group(1)))
        r_ = await c('undo_edits', {})
        return (ERROR if r_.is_error else '') + text(r_)

    t, same = await compared(ctx, undone_redone_undone)
    check(
        'undo_edits',
        "a step undone, then redone from code, is taken back again as the session's",
        not t.startswith(ERROR) and same and t.startswith("Undid 1 step, newest first: '%s'." % redone[0]),
        ('' if same else 'the graph changed | ') + t.strip()[-300:],
    )


async def check_undo_edits_names_another_clients_step_on_top_until_include_others(ctx: Ctx) -> None:
    """A call, then two steps of another client's on top of it (sd_run's, outside any undo group), which Designer names
    alike: undo_edits undoes nothing and names both; with include_others it undoes all three, each seen landing, the
    other client's marked as not the session's, and the graph is as before the call. include_others is sent only when
    the refusal named exactly those two steps, so a step made meanwhile, such as the user's, is never undone (REVIEW.md
    TST-888). The nodes a failure leaves are deleted after."""
    c, G = ctx.c, ctx.G
    seen = _Refusal()

    async def refused_then_undone_through() -> str:
        await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [600, 1200]}], **G})
        for _ in range(2):
            seen.others_ran.append((await asyncio.to_thread(sd_run, '-c', ADD)).returncode == 0)
        before = await described(ctx)
        seen.refused = await call_text(ctx, 'undo_edits', {})
        seen.kept = await described(ctx) == before
        found = re.search(r'sit on top of the calls asked for: (.*)\. Ask the user', seen.refused)
        seen.others = re.findall(r"'([^']+)'", found.group(1)) if found else []
        if seen.others_ran != [True, True] or len(seen.others) != 2:
            return ERROR + 'include_others not sent: the refusal named %s' % seen.others
        r_ = await c('undo_edits', {'include_others': True})
        return (ERROR if r_.is_error else '') + text(r_)

    t, same = await compared(ctx, refused_then_undone_through)
    others = seen.others
    check(
        'undo_edits',
        "another client's steps on top: nothing undone, the steps named",
        seen.others_ran == [True, True]
        and seen.refused.startswith(ERROR)
        and len(others) == 2
        and not any(other.startswith('Claude: ') for other in others)
        and 'include_others' in seen.refused
        and seen.kept,
        seen.refused.strip()[-300:] + ('' if seen.kept else ' | the graph changed'),
    )
    check(
        'undo_edits',
        "with include_others, the other client's steps undone too, each landing, marked, the graph as before the call",
        not t.startswith(ERROR)
        and same
        and len(others) == 2
        and ', '.join("'%s' (not this session's)" % other for other in others) in t
        and re.findall(SAID_STEP, t) == ['Claude: apply 1 edits'],
        ('' if same else 'the graph changed | ') + t.strip()[-300:],
    )


@dataclass
class _Refusal:
    """What check_undo_edits_names_another_clients_step_on_top_until_include_others saw before its last call: whether
    each other client's step was made, undo_edits' refusal and the steps it named, and whether the graph was kept."""

    others_ran: list[bool] = field(default_factory=list)
    refused: str = ''
    others: list[str] = field(default_factory=list)  # the steps the refusal named
    kept: bool = False


async def check_undo_edits_takes_a_reads_step_along_uncounted(ctx: Ctx) -> None:
    """An edit adding a node, a read of that node, which feeds no output, so the read adds a temporary output node and
    leaves a step (measured: preview_node, 2026-11-25), then another edit: undo_edits(count=2) takes back all three,
    the read's step marked and not counted, the edits' unmarked, and the graph is as before the first edit (REVIEW.md
    TST-875). The nodes a failure leaves are deleted after."""
    c, G = ctx.c, ctx.G

    async def edit_read_edit_undone() -> str:
        added = text(
            await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'uniform', 'position': [900, 1200]}], **G})
        )
        await c('preview_node', {'node_id': added_id(added), **G})
        await c(
            'apply_edits',
            {
                'ops': [
                    {'op': 'add', 'definition': 'blur', 'position': [1200, 1200]},
                    {'op': 'move', 'node': ctx.lv, 'position': [0, 0]},
                ],
                **G,
            },
        )
        return await call_text(ctx, 'undo_edits', {'count': 2})

    t, same = await compared(ctx, edit_read_edit_undone)
    check(
        'undo_edits',
        "a read's step between edits undone along, marked alone, not counted, and the edits taken back",
        not t.startswith(ERROR)
        and same
        and re.findall(SAID_STEP + READ_MARK, t)
        == [('Claude: apply 2 edits', ''), ('Claude: preview node', READ_SAID), ('Claude: apply 1 edits', '')],
        ('' if same else 'the graph changed | ') + t.strip()[-300:],
    )


async def check_undo_edits_takes_describe_nodes_steps_along_uncounted(ctx: Ctx) -> None:
    """An edit, then describe_node of an atomic node and of a library node, each of which made 8 or 9 steps of
    Designer's own (its temporary package and node, the library package it opens), now one tagged step a read:
    undo_edits() takes back all three, the two describe_node steps marked as reads, and the graph and the open
    packages are as before the edit (REVIEW.md SRV-265; measured 2026-11-25). The nodes a failure leaves are deleted
    after."""
    c, G = ctx.c, ctx.G
    packages: list[str] = []

    async def edit_described_undone() -> str:
        packages.append(await call_text(ctx, 'execute_designer_code', {'code': PACKAGES}))
        await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [1500, 1200]}], **G})
        for definition in ('blend', 'tile_generator'):
            await c('describe_node', {'definition': definition})
        t = await call_text(ctx, 'undo_edits', {})
        packages.append(await call_text(ctx, 'execute_designer_code', {'code': PACKAGES}))
        return t

    t, same = await compared(ctx, edit_described_undone)
    check(
        'undo_edits',
        "describe_node's steps after an edit undone along as reads, the graph and the packages as before",
        not t.startswith(ERROR)
        and same
        and re.findall(SAID_STEP + READ_MARK, t)
        == [('Claude: describe node', READ_SAID), ('Claude: describe node', READ_SAID), ('Claude: apply 1 edits', '')]
        and len(packages) == 2
        and 'PACKAGES=' in packages[0]
        and packages[0] == packages[1],
        ('' if same else 'the graph changed | ') + ' -> '.join(p.strip() for p in packages) + ' | ' + t.strip()[-300:],
    )


async def check_undo_edits_takes_search_nodes_scan_along_uncounted(ctx: Ctx) -> None:
    """A server's first search_nodes scans the library, and with no compositing graph in the editor (batch's
    preparation opens none) it makes a temporary package, which made 7 steps of Designer's own (REVIEW.md SRV-265's
    pattern; measured 2026-11-25). In a second client, a server of its own and so a scan of its own: an edit, then
    search_nodes, then undo_edits() takes back both, the scan's step marked as a read, and the graph and the open
    packages are as before the edit. With a graph in the editor, as a run in the user's Designer can have one, the scan
    may make no step (with a compositing graph there), and the check is skipped (REVIEW.md TST-877, TST-885). The nodes a failure leaves are deleted after."""
    in_editor = await graph_in_editor(ctx.c)
    if in_editor:
        skip('undo_edits', "search_nodes' scan after an edit undone along as a read", '%s is in the editor' % in_editor)
        return
    packages: list[str] = []

    async def in_a_server_of_its_own() -> str:
        packages.append(await call_text(ctx, 'execute_designer_code', {'code': PACKAGES}))
        async with stdio_client(common.PARAMS) as (r, w), ClientSession(r, w) as s:
            await s.initialize()
            await s.call_tool('get_guide', {})
            add = {'op': 'add', 'definition': 'blur', 'position': [2100, 1200]}
            await s.call_tool('apply_edits', {'ops': [add], **ctx.G})
            await s.call_tool('search_nodes', {'query': 'levels'})
            r_ = await s.call_tool('undo_edits', {})
        packages.append(await call_text(ctx, 'execute_designer_code', {'code': PACKAGES}))
        return (ERROR if r_.is_error else '') + text(r_)

    t, same = await compared(ctx, in_a_server_of_its_own)
    check(
        'undo_edits',
        "search_nodes' scan after an edit undone along as a read, the graph and the packages as before",
        not t.startswith(ERROR)
        and same
        and re.findall(SAID_STEP + READ_MARK, t) == [('Claude: search nodes', READ_SAID), ('Claude: apply 1 edits', '')]
        and len(packages) == 2
        and 'PACKAGES=' in packages[0]
        and packages[0] == packages[1],
        ('' if same else 'the graph changed | ') + ' -> '.join(p.strip() for p in packages) + ' | ' + t.strip()[-300:],
    )


async def check_undo_edits_refuses_calls_beyond_the_steps_listed(ctx: Ctx) -> None:
    """A call, then more steps of another client's on top of it than Designer's Undo dropdown lists (sd_run's, outside
    any undo group), then another call: undo_edits(count=2, include_others=True) undoes nothing, the second call's
    node still there, saying only one of the two calls is among the newest steps listed (REVIEW.md TST-876, TST-878:
    with no call listed, nothing could be undone anyway). undo_edits is sent only when both calls and all of BURY's
    steps were made, so that a failing setup never undoes a step of the user's (as TST-888 guards the include_others
    check). The nodes are deleted after, in one call."""
    c, G = ctx.c, ctx.G
    before = await described(ctx)
    try:
        made = [
            not (
                await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blur', 'position': [1800, 1200]}], **G})
            ).is_error
        ]
        ran = (await asyncio.to_thread(sd_run, '-c', BURY)).returncode == 0
        made.append(
            not (
                await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'blend', 'position': [1800, 1500]}], **G})
            ).is_error
        )
        before_undo = await described(ctx)
        if made == [True, True] and ran:
            refused = await call_text(ctx, 'undo_edits', {'count': 2, 'include_others': True})
        else:
            refused = 'undo_edits not sent: the calls made %s, all of BURY made %s' % (made, ran)
        unchanged = await described(ctx) == before_undo
    finally:
        left = sorted(set(positions(await described(ctx))) - set(positions(before)))
        if left:
            await c('apply_edits', {'ops': [{'op': 'delete', 'node': node} for node in left], **G})
    check(
        'undo_edits',
        'a call buried under more steps than the Undo list shows: nothing undone, and said',
        ran
        and refused.startswith(ERROR)
        and re.search(r'Undo list shows its newest \d+ steps, and only 1 of the 2 calls asked for', refused) is not None
        and unchanged,
        refused.strip()[-300:] + ('' if unchanged else ' | the graph changed'),
    )


async def check_the_undo_list_shows_the_newest_steps_only(ctx: Ctx) -> None:
    """Designer's Undo dropdown lists the newest designer_rollback.LISTED steps, the older ones still in its history:
    of one step more, the first made isn't listed until the top one is undone (batch/designer_scripts/listed_steps.py,
    run outside any undo group). undo_edits refuses calls asked for beyond them (the check before)."""
    r = sd_run(script_path('batch/listed_steps'), timeout=SCRIPT_S)
    found = re.search(r'^LISTED=(.*)$', r.stdout, re.M)
    said: dict[str, object] = json.loads(found.group(1)) if found else {}
    check(
        'designer facts',
        'the Undo dropdown lists the newest steps only, an older one shown once the top one is undone',
        r.returncode == 0
        and said.get('before') == said.get('most')
        and said.get('after') == said.get('most')
        and said.get('first_before') is False
        and said.get('first_after') is True
        and said.get('state') == 'undone',
        (r.stdout + r.stderr).strip()[-300:],
    )


async def check_a_timeout_never_leaves_a_calls_step_open(ctx: Ctx) -> None:
    """Calls whose code adds a node, then outlasts its timeout_s of 1 in one C call: the plugin's abort comes at the
    64th traced event once the limit is past. The first call's falls in its code, among 64 statements after that C
    call, on a line that tells which event after it ends the 64; that event moves with what Designer ran before, so
    it is measured here. Each call after it is aimed, by statements put before that C call, at the n-th traced event
    after its code, for each n of TIMED_AFTER. Each call's step is either rolled back (the rollback finds it listed on
    top before it takes it back) or listed on top of the Undo list, its node kept. None stays open (REVIEW.md
    SRV-273; server_tools/core.py, _with_undo). A step shown open (step_shown) is committed, so the calls and checks
    after it find Designer as before. The nodes kept are deleted after, in one call."""
    c, G = ctx.c, ctx.G
    await asyncio.to_thread(sd_run, '-c', BIND_GRAPH)
    top, nodes = _undo_top()
    added: list[str] = []
    opened: list[int] = []

    async def kept(t: str) -> bool:
        """Whether the step of the call that said `t` tops the Undo list, its node kept. A step left open is
        committed."""
        nonlocal top
        added.extend(re.findall(r'^ADDED=(\d+)$', t, re.M))
        now, count = _undo_top()
        shown = step_shown(now, top, count, nodes + len(added))
        if shown == 'open':
            await asyncio.to_thread(sd_run, '-c', COMMIT)
            now = _undo_top()[0]
        top = now
        return shown == 'listed'

    try:
        code = TIMED_OUT % ('', 'x = 1\n' * TRACED_EVERY)
        first = text(await c('execute_designer_code', {'code': code, 'timeout_s': 1}))
        lines = re.findall(r'File "<execute_designer_code>", line (\d+)', first)
        # the event after the C call that ends the 64: the line the abort fell on, the innermost frame's
        end = int(lines[-1]) - SLEEP_LINE if ROLLED_BACK in first and lines else 0
        if ROLLED_BACK not in first:  # the code tools give their error as text
            await kept(first)
        for after in TIMED_AFTER if end else ():
            # one event is the code's return
            code = TIMED_OUT % ('x = 1\n' * ((end - after - 1) % TRACED_EVERY), '')
            t = text(await c('execute_designer_code', {'code': code, 'timeout_s': 1}))
            if ROLLED_BACK not in t and not await kept(t):
                opened.append(after)
    finally:
        if added:
            await c('apply_edits', {'ops': [{'op': 'delete', 'node': node} for node in added], **G})
        await asyncio.to_thread(sd_run, '-c', UNBIND_GRAPH)
    check(
        'execute_designer_code',
        'a timeout falling in the code or anywhere after it leaves no step open: each listed or rolled back',
        end > 0 and not opened,
        "the first call wasn't rolled back from its code: " + first.strip()[-100:]
        if not end
        else 'aimed at events %s after the code, left open by %s' % (TIMED_AFTER, opened or 'none'),
    )


def step_shown(now: str, top: str, count: int, expected: int) -> Literal['listed', 'open', 'other']:
    """How Designer shows the step of a call of check_a_timeout_never_leaves_a_calls_step_open, from the Undo list's
    top `now` (`top` before the call) and the graph's `count` nodes (`expected` with the call's node): 'listed' on top,
    its node there; 'open', its node there and the top unchanged; or 'other'."""
    if count != expected:
        return 'other'
    if now == top:
        return 'open'
    return 'listed' if re.fullmatch(own_step('Claude: code'), now) else 'other'


def _undo_top() -> tuple[str, int]:
    """The newest step of the Undo dropdown ('' with none) and the self-test graph's node count
    (batch/designer_scripts/undo_top.py, run outside any undo group)."""
    r = sd_run(script_path('batch/undo_top'), timeout=SCRIPT_S)
    top = re.search(r'^TOP=(.*)$', r.stdout, re.M)
    count = re.search(r'^NODES=(\d+)$', r.stdout, re.M)
    if not (top and count):
        raise RuntimeError('batch/undo_top printed no state: ' + (r.stdout + r.stderr).strip()[-200:])
    name: str | None = json.loads(top.group(1))
    return name or '', int(count.group(1))
