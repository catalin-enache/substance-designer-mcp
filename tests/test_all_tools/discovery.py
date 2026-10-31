"""Finding nodes: search_nodes and describe_node."""

from .common import Ctx, check, text


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
    t = text(await c('describe_node', {'definition': 'blend'}))
    check('describe_node', 'atomic enum', 'max=5' in t, '')
    t = text(await c('describe_node', {'definition': 'slope_blur.sbs/slope_blur_grayscale_2'}))
    check('describe_node', 'library', "output connector ids: ['Slope_Blur']" in t, t.splitlines()[0])
