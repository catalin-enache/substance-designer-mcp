"""What functions' checks of set_function and of the tools reading functions read: the self-test graph, 16 px, holding
- a Pixel Processor, its $randomseed 7 and its $outputsize Absolute at 8 px, feeding an output;
- a Value Processor;
- a uniform black colour through a levels node, its levelinhigh 0.9, to an output;
- a blend of a uniform white colour over that black, to an output: its pixels are its opacity;
- the graph input `tint`, a colour (0.4, 0.6, 0.8, 1), exposed from a uniform's colour that feeds nothing;
- an image to sample, `ramp.png` as a bitmap: 4 px, its columns' R and its rows' G the bytes of RAMP, B 128;
- a normal map: Designer's normal node on `bump.png`, a 16 px bitmap of a tiling bump, at intensity 100."""

import math
import os

from test_all_tools.common import TEST_GRAPH, Ctx, Ops, prepared_call, refs

RAMP = (32, 96, 159, 223)  # the bytes of ramp.png's columns (R) and rows (G): 0.125 to 0.875, as Designer stores them


def _images(folder: str) -> tuple[str, str]:
    """ramp.png and bump.png written in `folder`: their paths."""
    from PIL import Image

    ramp, bump = os.path.join(folder, 'ramp.png'), os.path.join(folder, 'bump.png')
    image = Image.new('RGB', (4, 4))
    image.putdata([(r, g, 128) for g in RAMP for r in RAMP])
    image.save(ramp)
    heights = Image.new('L', (16, 16))
    wave = [math.sin(2 * math.pi * k / 16) for k in range(16)]
    heights.putdata([round(128 + 100 * wave[x] * wave[(y + 4) % 16]) for y in range(16) for x in range(16)])
    heights.save(bump)
    return ramp, bump


async def prepare(ctx: Ctx) -> None:
    c = ctx.c
    await prepared_call(c, 'create_graph', {'name': TEST_GRAPH, 'size_log2': 4})
    ctx.G = {'graph': TEST_GRAPH}
    ramp, bump = _images(ctx.scratch)
    ops: Ops = [
        {'op': 'add', 'definition': 'pixelprocessor', 'ref': 'pp', 'params': {'$randomseed': 7, '$outputsize': [3, 3]}},
        {'op': 'add', 'definition': 'output', 'ref': 'out'},
        {'op': 'connect', 'from': 'pp', 'to': 'out', 'input': 'inputNodeOutput'},
        {'op': 'add', 'definition': 'valueprocessor', 'ref': 'vp'},
        {'op': 'add', 'definition': 'uniform', 'ref': 'black', 'params': {'outputcolor': [0, 0, 0, 1]}},
        {'op': 'add', 'definition': 'levels', 'ref': 'lv', 'params': {'levelinhigh': [0.9, 0.9, 0.9, 1]}},
        {'op': 'connect', 'from': 'black', 'to': 'lv', 'input': 'input1'},
        {'op': 'add', 'definition': 'output', 'ref': 'lout'},
        {'op': 'connect', 'from': 'lv', 'to': 'lout', 'input': 'inputNodeOutput'},
        {'op': 'add', 'definition': 'uniform', 'ref': 'white', 'params': {'outputcolor': [1, 1, 1, 1]}},
        {'op': 'add', 'definition': 'blend', 'ref': 'blend'},
        {'op': 'connect', 'from': 'white', 'to': 'blend', 'input': 'source'},
        {'op': 'connect', 'from': 'black', 'to': 'blend', 'input': 'destination'},
        {'op': 'add', 'definition': 'output', 'ref': 'bout'},
        {'op': 'connect', 'from': 'blend', 'to': 'bout', 'input': 'inputNodeOutput'},
        {'op': 'add', 'definition': 'uniform', 'ref': 'colour'},
        {'op': 'expose', 'node': 'colour', 'param': 'outputcolor', 'input_id': 'tint', 'default': [0.4, 0.6, 0.8, 1]},
        {'op': 'bitmap', 'path': ramp, 'ref': 'img'},
        {'op': 'bitmap', 'path': bump, 'ref': 'bump'},
        {'op': 'add', 'definition': 'normal', 'ref': 'nm', 'params': {'intensity': 100}},
        {'op': 'connect', 'from': 'bump', 'to': 'nm', 'input': 'input1'},
    ]
    added = refs(await prepared_call(c, 'apply_edits', {'ops': ops, **ctx.G}))
    ctx.pp = added['pp']
    ctx.vp = added['vp']
    ctx.lv = added['lv']
    ctx.out = added['out']
    ctx.blend = added['blend']
    ctx.img = added['img']
    ctx.nm = added['nm']
