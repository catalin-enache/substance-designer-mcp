"""The self-test graph and its first nodes: create_graph and apply_edits' add op."""

import os
from textwrap import dedent

from test_all_tools.common import SAVED_GRAPH, TEST_GRAPH, Ctx, added_id, check, designer_script, text


async def run(ctx: Ctx) -> None:
    """Creates the self-test graph and its first nodes."""
    c, scratch, helper_source = ctx.c, ctx.scratch, ctx.helper_source
    # --- build a temporary graph with the edit tools
    t = text(await c('create_graph', {'name': TEST_GRAPH, 'size_log2': 9}))
    check('create_graph', '512 px', '(512 px)' in t, t)
    saved_sbs = os.path.join(scratch, SAVED_GRAPH + '.sbs')
    t = text(await c('create_graph', {'name': SAVED_GRAPH, 'save_path': saved_sbs, 'size_log2': 8}))
    check('create_graph', 'save_path writes the .sbs', os.path.isfile(saved_sbs), t)
    G = {'graph': TEST_GRAPH}
    await c('open_graph', {'graph': TEST_GRAPH})  # so you can watch the nodes appear
    r_ = await c('diff_graph', {'against': 'saved', **G})
    check('diff_graph', 'error: never saved', r_.is_error and 'never been saved' in text(r_), text(r_))
    r_ = await c('diff_graph', {'against': 'latest', 'graph': SAVED_GRAPH})
    check('diff_graph', 'error: no snapshots yet', r_.is_error and 'no snapshots of' in text(r_), text(r_))
    t = text(
        await c(
            'apply_edits',
            {'ops': [{'op': 'add', 'definition': 'noise_clouds_2.sbs/clouds_2', 'params': {'scale': 4}}], **G},
        )
    )
    check('apply_edits', 'add: library + param', 'instance:clouds_2' in t and '-> 4' in t, t)
    added_id(t)
    added_id(
        text(
            await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'slope_blur.sbs/slope_blur_grayscale_2'}], **G})
        )
    )
    t = text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels'}], **G}))
    check('apply_edits', 'add: atomic', 'levels' in t, t.splitlines()[0])
    added_id(t)
    added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'output'}], **G})))
    r_ = await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'not_a_real_node'}], **G})
    check('apply_edits', 'add: error on unknown type', r_.is_error and 'neither an atomic' in text(r_), '')
    # a bad param refuses the whole add, and says so: the node isn't left behind (REVIEW.md HLP-30)
    before = text(await designer_script(c, 'shared/count_nodes', graph=TEST_GRAPH))
    r_ = await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels', 'params': {'levelinhigh': 0.5}}], **G})
    after = text(await designer_script(c, 'shared/count_nodes', graph=TEST_GRAPH))
    # if removing it fails too, both errors are reported (REVIEW.md HLP-37)
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helper_source
                + (
                    dedent("""
                        g = find_graph(%r); had = {n.getIdentifier() for n in g.getNodes()}
                        real = SDSBSCompGraph.deleteNode
                        def failing(self, node):
                            raise RuntimeError('delete failed on purpose')
                        SDSBSCompGraph.deleteNode = failing
                        try:
                            add_node(%r, 'levels', None, {'levelinhigh': 0.5})
                        except Exception as e:
                            print('ERROR=' + str(e))
                        finally:
                            # it is SDGraph's: leave no copy behind (TST-73)
                            del SDSBSCompGraph.deleteNode
                            for n in [n for n in g.getNodes() if n.getIdentifier() not in had]:
                                g.deleteNode(n)
                    """)
                )
                % (TEST_GRAPH, TEST_GRAPH)
            },
        )
    )
    check(
        'apply_edits',
        'add: a failed removal is reported with the error that caused it',
        'expects 4' in t and 'delete failed on purpose' in t,
        t.strip()[-200:],
    )
    check(
        'apply_edits',
        'add: a bad param leaves no node behind, and says so',
        r_.is_error and 'expects 4' in text(r_) and 'not added' in text(r_) and before == after and 'NODES=' in before,
        text(r_).strip()[-120:] + ' | ' + before.strip() + ' -> ' + after.strip(),
    )
