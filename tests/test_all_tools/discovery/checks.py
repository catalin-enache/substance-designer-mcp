"""Finding nodes: search_nodes and describe_node."""

import os
import re
from textwrap import dedent

from test_all_tools.common import ABORT_AT, Ctx, check, helper_lines, text

# a package made and unloaded: what was listed before it, the one new, then as before (designer facts, the helpers'
# _unload_new_packages relies on them: describe.py)
NEW_PACKAGE = dedent("""
    def listed():
        return [(p.getUID(), p.getFilePath() or '') for p in _PM.getUserPackages()]
    before = listed()
    new = _PM.newUserPackage()
    made = new.getUID()
    after = listed()
    _PM.unloadUserPackage(new)
    print('NEW=%r BACK=%r' % ([entry for entry in after if entry not in before] == [(made, '')], listed() == before))
""")


async def check_a_package_made_has_a_uid_of_its_own_and_no_file_and_goes_once_unloaded(ctx: Ctx) -> None:
    """A user package made by the API is listed with a UID none of the packages listed before has, and no file;
    unloaded, the list is as before (designer facts: describe.py's _unload_new_packages finds the packages a call made
    by them, unloading none twice, which crashed Designer: REVIEW.md HLP-177)."""
    t = text(await ctx.c('execute_designer_code', {'code': ctx.helper_source + NEW_PACKAGE}))
    check(
        'designer facts',
        'a package made has a UID of its own and no file, and the list is as before once it is unloaded',
        'NEW=True BACK=True' in t,
        t.strip()[-150:],
    )


# describe_node, aborted at the first of __LINES__ it reaches (common.ABORT_AT); the packages it left, then unloaded for
# the checks after it
DESCRIBE_ABORTED = dedent("""
    before = {p.getUID() for p in _PM.getUserPackages()}
    _aborted_at(__LINES__, lambda: describe_node('levels'))
    left = [p for p in _PM.getUserPackages() if p.getUID() not in before]
    print('LEFT=%d' % len(left))
    for p in left:
        _PM.unloadUserPackage(p)
""")


async def check_an_abort_unloading_describe_nodes_package_still_unloads_it(ctx: Ctx) -> None:
    """An abort landing on describe_node's unload of the package it makes still unloads it (REVIEW.md HLP-177: it was
    left in the user's Explorer). The abort is the plugin's, raised by a tracer of the check's at that line."""
    lines = helper_lines(ctx.helper_source, r'_PM\.unloadUserPackage\(')
    code = ctx.helper_source + ABORT_AT + DESCRIBE_ABORTED.replace('__LINES__', repr(lines))
    t = text(await ctx.c('execute_designer_code', {'code': code}))
    left = re.search(r'LEFT=(\d+)', t)
    check(
        'describe_node',
        "an abort unloading describe_node's package still unloads it",
        'ABORTED' in t and left is not None and left.group(1) == '0',
        t.strip()[-150:],
    )


async def run(ctx: Ctx) -> None:
    c = ctx.c
    # --- discovery
    t = text(await c('search_nodes', {'query': 'slope blur'}))
    check('search_nodes', 'library hit', 'slope_blur.sbs/slope_blur_grayscale_2' in t, t.splitlines()[0])
    t = text(await c('search_nodes', {'query': 'levels', 'limit': 2}))
    check('search_nodes', 'atomic ranked first', t.startswith('atomic   levels'), t.splitlines()[0])
    hidden = "definition='3d_texture_jump_flood'"  # hideInLibrary=1 in Designer 16
    shown = text(await c('search_nodes', {'query': 'jump flood'}))
    all_ = text(await c('search_nodes', {'query': 'jump flood', 'include_hidden': True}))
    check('search_nodes', 'include_hidden adds hidden graphs', hidden not in shown and hidden in all_, all_)
    # a ready-made material in a subfolder of the library (ROADMAP item 41). Its name is Designer 16's
    t = text(await c('search_nodes', {'query': 'bricks 001'}))
    check(
        'search_nodes',
        'finds a material in a subfolder',
        "definition='materials/pbr/bricks_001'" in t,
        t.splitlines()[0],
    )
    t = text(await c('describe_node', {'definition': 'materials/pbr/bricks_001'}))
    check(
        'describe_node',
        'a material in a subfolder',
        "'basecolor'" in t and 'library node bricks_001' in t,
        t.splitlines()[0],
    )
    # a real .sbs outside the library is refused for being outside, not for being missing (TST-113)
    outside = os.path.join(ctx.scratch, 'outside_library.sbs')
    with open(outside, 'w', encoding='utf-8') as f:
        f.write('<package/>')
    r_ = await c('describe_node', {'definition': outside})
    check(
        'describe_node',
        'a definition stays in the library folder',
        r_.is_error and '(outside ' in text(r_),
        text(r_)[-150:],
    )
    # the graph part is looked up inside the package, so it can't leave it either (REVIEW.md HLP-61)
    r_ = await c('describe_node', {'definition': 'hbao.sbs/../bevel'})
    check(
        'describe_node',
        "a definition's graph stays in its package",
        r_.is_error and 'not found in' in text(r_),
        text(r_)[-150:],
    )
    # a graph in a group is named with its group, and that name works (REVIEW.md SRV-56)
    t = text(await c('search_nodes', {'query': 'constant float', 'limit': 3}))
    check(
        'search_nodes',
        'names a grouped graph with its group',
        "definition='constant_values.sbs/float/constant_float'" in t,
        t.splitlines()[0],
    )
    t = text(await c('describe_node', {'definition': 'constant_values.sbs/float/constant_float'}))
    check('describe_node', 'a grouped graph', 'library node float/constant_float' in t, t.splitlines()[0])
    t = text(await c('describe_node', {'definition': 'materials/pbr/fabric_002.sbs/Resources/stains'}))
    check('describe_node', 'a grouped graph in a subfolder', 'library node Resources/stains' in t, t.splitlines()[0])
    # a group is told apart from a graph: Designer only says NotSupported (REVIEW.md HLP-63)
    r_ = await c('describe_node', {'definition': 'constant_values.sbs/float'})
    check(
        'describe_node',
        'a definition naming a group says so',
        r_.is_error and 'names a group' in text(r_),
        text(r_)[-150:],
    )
    # a material Designer hides isn't reported as absent (REVIEW.md SRV-55)
    t = text(await c('search_nodes', {'query': 'concrete pavement'}))
    check('search_nodes', 'says when hidden graphs match', 'hidden graph(s) match too: include_hidden=True' in t, t)
    t = text(await c('describe_node', {'definition': 'blend'}))
    check('describe_node', 'atomic enum', 'max=5' in t, '')
    t = text(await c('describe_node', {'definition': 'slope_blur.sbs/slope_blur_grayscale_2'}))
    check('describe_node', 'library', "output connector ids: ['Slope_Blur']" in t, t.splitlines()[0])
    await check_a_package_made_has_a_uid_of_its_own_and_no_file_and_goes_once_unloaded(ctx)
    await check_an_abort_unloading_describe_nodes_package_still_unloads_it(ctx)
