"""What params' checks read: the self-test graph at 512 px (its size set to 10 must change it) with a clouds_2
instance (its seed's effect is computed), a slope blur (an int Samples, a float Intensity) and a levels node (a float4
levelinlow), unconnected, every parameter, inheritance and seed at a new node's default. Below them, a grey ramp of
five bands (a grayscale Pixel Processor reading 0, 0.25, 0.5, 0.75 and 1 from left to right) feeds a Gradient Map and a
Curve, neither given keys, each feeding an output."""

from test_all_tools.common import TEST_GRAPH, Ctx, prepared_call, refs


async def prepare(ctx: Ctx) -> None:
    c = ctx.c
    await prepared_call(c, 'create_graph', {'name': TEST_GRAPH, 'size_log2': 9})
    ctx.G = {'graph': TEST_GRAPH}
    added = refs(
        await prepared_call(
            c,
            'apply_edits',
            {
                'ops': [
                    {'op': 'add', 'definition': 'noise_clouds_2.sbs/clouds_2', 'ref': 'clouds', 'position': [-600, 0]},
                    {
                        'op': 'add',
                        'definition': 'slope_blur.sbs/slope_blur_grayscale_2',
                        'ref': 'slope',
                        'position': [-300, 0],
                    },
                    {'op': 'add', 'definition': 'levels', 'ref': 'lv', 'position': [0, 0]},
                    {
                        'op': 'add',
                        'definition': 'pixelprocessor',
                        'ref': 'ramp',
                        'position': [-300, 300],
                        'params': {'colorswitch': False},
                    },
                    {'op': 'add', 'definition': 'gradient', 'ref': 'gradient', 'position': [0, 300]},
                    {'op': 'add', 'definition': 'curve', 'ref': 'curve', 'position': [0, 500]},
                    {'op': 'connect', 'from': 'ramp', 'to': 'gradient', 'input': 'input1'},
                    {'op': 'connect', 'from': 'ramp', 'to': 'curve', 'input': 'input1'},
                    # outputs, so the first compute of node_stats and sweep_param gives the two textures
                    {'op': 'add', 'definition': 'output', 'ref': 'gradient_out', 'position': [300, 300]},
                    {'op': 'add', 'definition': 'output', 'ref': 'curve_out', 'position': [300, 500]},
                    {'op': 'connect', 'from': 'gradient', 'to': 'gradient_out', 'input': 'inputNodeOutput'},
                    {'op': 'connect', 'from': 'curve', 'to': 'curve_out', 'input': 'inputNodeOutput'},
                ],
                **ctx.G,
            },
        )
    )
    ctx.clouds = added['clouds']
    ctx.slope = added['slope']
    ctx.lv = added['lv']
    ctx.ramp = added['ramp']
    ctx.gradient = added['gradient']
    ctx.curve = added['curve']
    await prepared_call(c, 'set_function', {'expression': 'floor($pos.x * 5) / 4', 'node_id': ctx.ramp, **ctx.G})
