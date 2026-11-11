"""Finding nodes: search_nodes and describe_node."""

import os

from test_all_tools.common import Ctx, check, text


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
