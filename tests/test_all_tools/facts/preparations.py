"""What facts' checks read: the self-test graph at exactly 512 px (a gradient sampled at its bottom row), a slope
blur connected into a levels node's input1 (the sd API facts about a connection), and a PNG on disk, also as a bitmap
node in the graph (the save round trip strips its dependency path: SRV-70). The levels node feeds an output, has a
parameter set and one driven by the graph input `floor` (what the save round trip compares: values, an input and a
function graph), and the graph has a default parent size (embed_and_parent_size puts it back: create_graph's graph has
none, which setDefaultParentSize refuses), overridable at 512 px. The graph is open in the editor, so the 3D view
shows it. In a Designer the self-test started, the state file checks' graph, left closed: two outputs of one colour,
base colour and roughness (STATE_GRAPH)."""

import os

from test_all_tools.common import TEST_GRAPH, Ctx, Ops, prepared_call, refs

STATE_GRAPH = 'mcp_selftest_state_file'  # its outputs on the mesh: their textures saved beside the state file
# two outputs, so Designer maps them by usage rather than asking which channel to show a single one in
STATE_OPS: Ops = [
    {'op': 'add', 'definition': 'uniform', 'ref': 'n', 'position': [-300, 0]},
    {'op': 'add', 'definition': 'output', 'ref': 'o', 'usage': 'baseColor', 'identifier': 'basecolor'},
    {'op': 'connect', 'from': 'n', 'to': 'o', 'input': 'inputNodeOutput'},
    {
        'op': 'add',
        'definition': 'output',
        'ref': 'r',
        'usage': 'roughness',
        'identifier': 'roughness',
        'position': [0, 150],
    },
    {'op': 'connect', 'from': 'n', 'to': 'r', 'input': 'inputNodeOutput'},
]


async def prepare(ctx: Ctx) -> None:
    c = ctx.c
    await prepared_call(c, 'create_graph', {'name': TEST_GRAPH, 'size_log2': 9})
    ctx.G = {'graph': TEST_GRAPH}
    from PIL import Image

    ctx.png = os.path.join(ctx.scratch, 'selftest_bitmap.png')
    Image.new('RGB', (64, 32), (200, 100, 50)).save(ctx.png)
    added = refs(
        await prepared_call(
            c,
            'apply_edits',
            {
                'ops': [
                    {
                        'op': 'add',
                        'definition': 'slope_blur.sbs/slope_blur_grayscale_2',
                        'ref': 'slope',
                        'position': [-300, 0],
                    },
                    {
                        'op': 'add',
                        'definition': 'levels',
                        'ref': 'lv',
                        'position': [0, 0],
                        'params': {'levelinhigh': [0.8] * 4},
                    },
                    {'op': 'add', 'definition': 'output', 'ref': 'out', 'position': [300, 0]},
                    {'op': 'connect', 'from': 'slope', 'to': 'lv', 'input': 'input1'},
                    {'op': 'connect', 'from': 'lv', 'to': 'out', 'input': 'inputNodeOutput'},
                    {'op': 'bitmap', 'path': ctx.png, 'position': [-600, 300]},
                    {'op': 'expose', 'node': 'lv', 'param': 'leveloutlow', 'input_id': 'floor', 'default': [0.25] * 4},
                ],
                **ctx.G,
            },
        )
    )
    ctx.slope = added['slope']
    ctx.lv = added['lv']
    await prepared_call(c, 'set_graph_size', {'size_log2': 9, 'overridable': True, **ctx.G})
    await prepared_call(c, 'open_graph', ctx.G)  # its 3D view: a Designer just started has none, with no graph open
    if not ctx.was_running:  # the state file checks, which use it, skip in the user's Designer
        await prepared_call(c, 'create_graph', {'name': STATE_GRAPH, 'size_log2': 8})  # not opened: the editor stays
        await prepared_call(c, 'apply_edits', {'graph': STATE_GRAPH, 'ops': STATE_OPS})
