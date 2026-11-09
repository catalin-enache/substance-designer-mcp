"""Output: export_outputs, sbsar_info, render_sbs (seeds, sizes, formats) and preview_maps."""

import os
import re
import subprocess
import sys
from textwrap import dedent
from typing import Any

from .common import BUNDLE, TEST_GRAPH, Ctx, _mean_png, check, designer_script, helpers_source, is_image, text


async def run(ctx: Ctx) -> None:
    c, scratch, G, clouds, sbs = ctx.c, ctx.scratch, ctx.G, ctx.clouds, ctx.sbs
    t = text(await c('export_outputs', {'graph': TEST_GRAPH, 'output_dir': os.path.join(scratch, 'export')}))
    check('export_outputs', 'from Designer', 'height.png  512x512' in t, t)
    # an output node with nothing connected: exported, or named as computing no image; never left
    # out without a word (REVIEW.md HLP-48)
    empty = re.search(
        r'EMPTY=(\d+)',
        text(await designer_script(c, 'render/add_output', graph=TEST_GRAPH, identifier='mcp_empty', label='EMPTY')),
    )
    try:
        r_ = await c(
            'export_outputs',
            {
                'graph': TEST_GRAPH,
                'output_dir': os.path.join(scratch, 'export_empty'),
                'outputs': ['height', 'mcp_empty'],
            },
        )
        # exported: an unconnected output still computes an image, the fact HLP-48's "not reproduced"
        # rests on; the node must exist, or the check would measure nothing (REVIEW.md TST-100)
        check(
            'export_outputs',
            'an output with nothing connected still computes an image, and is exported',
            empty is not None and 'mcp_empty.png' in text(r_),
            text(r_).strip()[-200:],
        )
    finally:
        if empty:
            await c('apply_edits', {'ops': [{'op': 'delete', 'node': empty.group(1)}], **G})
    t = text(await c('sbsar_info', {'sbs_path': sbs}))
    check('sbsar_info', 'graph + output', 'pkg://%s' % TEST_GRAPH in t and 'OUTPUT height' in t, t.splitlines()[0])
    # the graph seed set with a set op is still a control of the cooked graph (REVIEW.md HLP-25)
    check(
        'sbsar_info',
        'the graph seed set with a set op is still exposed',
        'INPUT $randomseed' in t,
        ' / '.join(l for l in t.splitlines() if 'INPUT' in l),
    )
    # and an Absolute one is not (GUIDE.md): a copy saved with it Absolute, the graph put back;
    # changing the inheritance resets the value, so the value goes back after it
    abs_sbs = os.path.join(scratch, 'seed_absolute.sbs')
    await designer_script(c, 'render/absolute_seed_copy', graph=TEST_GRAPH, path=abs_sbs)
    t_abs = text(await c('sbsar_info', {'sbs_path': abs_sbs}))
    check(
        'designer facts',
        'an Absolute graph $randomseed is not exposed in a .sbsar (GUIDE.md)',
        'INPUT $outputsize' in t_abs and 'INPUT $randomseed' not in t_abs,
        ' / '.join(l for l in t_abs.splitlines() if 'INPUT' in l),
    )
    # the stored seed (5) reaches the .sbsar too, added to the seed a render sets (GUIDE.md: "its
    # value is added to its parent's seed"; REVIEW.md TST-39, TST-44): copies storing 0 and 3 to compare
    seed_copies = {}
    for stored_seed in (0, 3):  # copies of the graph storing another seed
        seed_copies[stored_seed] = os.path.join(scratch, 'seed_stored%d.sbs' % stored_seed)
        await designer_script(
            c, 'render/stored_seed_copy', graph=TEST_GRAPH, seed=stored_seed, path=seed_copies[stored_seed]
        )
    zero_sbs = seed_copies[0]
    # and one with the clouds node's seed made Absolute (REVIEW.md TST-52); the graph's untouched
    abs_node_sbs = os.path.join(scratch, 'seed_absolute_node.sbs')
    await designer_script(c, 'render/node_seed_absolute_copy', graph=TEST_GRAPH, node=clouds, path=abs_node_sbs)
    import numpy as np
    from PIL import Image

    # both count: the stored value (5 vs 0 at render seed 0) and the render seed (0 vs 5 for the
    # copy storing 0), so neither replaces the other (REVIEW.md TST-40)
    seed_maps: dict[str, Any] = {}  # numpy arrays, or None where a render made no file
    render_said: dict[str, str] = {}
    for name, path, seed in (
        ('stored5_seed0', sbs, 0),
        ('stored0_seed0', zero_sbs, 0),
        ('stored0_seed5', zero_sbs, 5),
        ('stored3_seed2', seed_copies[3], 2),
        ('abs_node_seed0', abs_node_sbs, 0),
        ('abs_node_seed5', abs_node_sbs, 5),
    ):
        d = os.path.join(scratch, 'seed_render_' + name)
        t_r = text(
            await c(
                'render_sbs',
                {'sbs_path': path, 'output_dir': d, 'outputs': ['height'], 'params': {'$randomseed': seed}},
            )
        )
        render_said[name] = t_r
        f = os.path.join(d, 'height.png')
        seed_maps[name] = np.array(Image.open(f)).astype(int) if os.path.isfile(f) else None

    def apart(a: str, b: str) -> int:
        ma, mb = seed_maps[a], seed_maps[b]
        return int(np.abs(ma - mb).max()) if ma is not None and mb is not None and ma.shape == mb.shape else -1

    stored, override = apart('stored5_seed0', 'stored0_seed0'), apart('stored0_seed0', 'stored0_seed5')
    # added: 3 + 2 gives the image of 0 + 5, within the parallel render noise (8, as export vs
    # render); a pair without zeros, since 5 + 0 = 0 + 5 also fits max, OR or XOR (REVIEW.md TST-44)
    added = apart('stored3_seed2', 'stored0_seed5')
    check(
        'designer facts',
        'an inherited graph seed stored in the .sbsar is added to the render seed (GUIDE.md)',
        stored > 8 and override > 8 and 0 <= added <= 8,
        'max difference: stored value %d, render seed %d, 3+2 vs 0+5 %d (/65535)%s'
        % (stored, override, added, '' if min(stored, override, added) >= 0 else ' | ' + t_r[-150:]),
    )
    # a node seed made Absolute ignores the render's seed: its noise is the same at render seed 0
    # and 5 (the height output's only randomness is that clouds node), while the copy where it
    # follows the graph changes (REVIEW.md TST-52)
    frozen = apart('abs_node_seed0', 'abs_node_seed5')
    # and the render seed did reach that copy: render_sbs only warns when an input isn't exposed
    # (REVIEW.md TST-58)
    reached = not any('is not exposed' in render_said[k] for k in ('abs_node_seed0', 'abs_node_seed5'))
    check(
        'designer facts',
        "a node $randomseed made Absolute ignores the render's seed (GUIDE.md)",
        0 <= frozen <= 8 and override > 8 and reached,
        'max difference: Absolute node, render seed 0 vs 5: %d; '
        'inherited: %d (/65535); render seed exposed: %s' % (frozen, override, reached),
    )
    # and back to a new graph's seed for the later checks (REVIEW.md TST-37)
    t = text(await c('apply_edits', {'ops': [{'op': 'set', 'node': 'graph', 'params': {'$randomseed': 0}}], **G}))
    check('self-test', 'the graph seed checks put the seed back as it was', '5 -> 0' in t, t)
    render_dir = os.path.join(scratch, 'render')
    t = text(await c('render_sbs', {'sbs_path': sbs, 'output_dir': render_dir, 'outputs': ['height']}))
    check('render_sbs', 'png', 'height.png  512x512' in t, t)
    import numpy as np
    from PIL import Image

    exported = np.array(Image.open(os.path.join(scratch, 'export', 'height.png'))).astype(int)
    rendered = np.array(Image.open(os.path.join(render_dir, 'height.png'))).astype(int)
    # the same to within a few 16-bit steps at a few pixels (GUIDE.md, Output; seen: 27 of
    # 262144 pixels off by <= 3/65535); parallel renders aren't bit-identical, so allow 8
    worst = np.abs(exported - rendered).max() if exported.shape == rendered.shape else -1
    check(
        'export_outputs',
        'matches render_sbs within 16-bit rounding',
        0 <= worst <= 8,
        'max difference %d/65535, %d pixel(s) differ' % (worst, int((exported != rendered).sum())),
    )
    t = text(
        await c(
            'export_outputs',
            {
                'graph': TEST_GRAPH,
                'output_dir': os.path.join(scratch, 'export_exr'),
                'outputs': ['height'],
                'file_format': 'exr',
            },
        )
    )
    check(
        'export_outputs',
        'subset + exr',
        'height.exr' in t and os.path.isfile(os.path.join(scratch, 'export_exr', 'height.exr')),
        t,
    )
    r_ = await c(
        'export_outputs', {'graph': TEST_GRAPH, 'output_dir': os.path.join(scratch, 'none'), 'outputs': ['nope']}
    )
    check('export_outputs', 'error on unknown output', r_.is_error and 'no outputs exported' in text(r_), text(r_))
    # a requested name that matches nothing is reported, and two outputs with one name are refused
    # rather than written to one file (REVIEW.md HLP-34)
    t = text(
        await c(
            'export_outputs',
            {'graph': TEST_GRAPH, 'output_dir': os.path.join(scratch, 'typo'), 'outputs': ['height', 'heigth']},
        )
    )
    check('export_outputs', 'a requested name that matches nothing is reported', 'height.png' in t and 'heigth' in t, t)
    # ...and when none matches, the error lists the outputs there are (REVIEW.md HLP-36)
    r_ = await c(
        'export_outputs', {'graph': TEST_GRAPH, 'output_dir': os.path.join(scratch, 'typo2'), 'outputs': ['heigth']}
    )
    check(
        'export_outputs',
        'a request matching nothing lists the outputs',
        r_.is_error and 'height' in text(r_).replace('heigth', ''),
        text(r_).strip()[-150:],
    )
    twin = text(await designer_script(c, 'render/add_output', graph=TEST_GRAPH, identifier='Height', label='TWIN'))
    twin_id = re.search(r'TWIN=(\S+)', twin)
    r_ = await c('export_outputs', {'graph': TEST_GRAPH, 'output_dir': os.path.join(scratch, 'twins')})
    # 'Height' and 'height': one file on macOS and Windows file systems (REVIEW.md HLP-36)
    check(
        'export_outputs',
        'two outputs with one name (in any case) are refused',
        r_.is_error
        and 'height' in text(r_).lower()
        and not os.path.exists(os.path.join(scratch, 'twins', 'height.png')),
        text(r_).strip()[-150:],
    )
    if twin_id:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': twin_id.group(1)}], **G})
    t = text(await c('sbsar_info', {'sbs_path': sbs}))
    check('sbsar_info', 'exposed input + size', 'INPUT floor FLOAT4' in t and 'INPUT $outputsize' in t, '')
    means = []
    for v in (0.1, 0.9):
        d = os.path.join(scratch, 'floor_%s' % v)
        t = text(
            await c('render_sbs', {'sbs_path': sbs, 'output_dir': d, 'size_log2': 7, 'params': {'floor': [v] * 4}})
        )
        means.append(t)
    check('render_sbs', 'size override 128', 'height.png  128x128' in means[0], means[0])
    check(
        'render_sbs',
        'exposed param changes output',
        _mean_png(os.path.join(scratch, 'floor_0.1', 'height.png')) + 0.3
        < _mean_png(os.path.join(scratch, 'floor_0.9', 'height.png')),
        '',
    )
    t = text(
        await c(
            'render_sbs', {'sbs_path': sbs, 'output_dir': render_dir, 'output_format': 'exr', 'params': {'nope': 1}}
        )
    )
    check('render_sbs', 'exr + unexposed warning', 'height.exr' in t and "input 'nope' is not exposed" in t, t)
    check(
        'render_sbs',
        'cooking leaves no .sbsar next to the .sbs',
        not os.path.exists(os.path.splitext(sbs)[0] + '.sbsar'),
        '',
    )
    sys.path.insert(0, os.path.join(BUNDLE, 'mcp_server'))
    import server as mcp_server_module  # for the sbscooker path only

    cooked = os.path.join(scratch, 'cooked')
    os.makedirs(cooked, exist_ok=True)  # sbscooker needs the folder to exist
    # SBSCOOKER: server_tools.core's, re-exported by server.py at runtime
    subprocess.run(
        [mcp_server_module.SBSCOOKER, '--inputs', sbs, '--output-path', cooked],  # type: ignore[attr-defined]
        capture_output=True,
        timeout=300,
    )
    sbsar = os.path.join(cooked, TEST_GRAPH + '.sbsar')
    t = text(await c('sbsar_info', {'sbs_path': sbsar}))
    check('sbsar_info', 'reads a .sbsar', 'OUTPUT height' in t, t.splitlines()[0] if t else '')
    t = text(
        await c(
            'render_sbs',
            {
                'sbs_path': sbsar,
                'output_dir': os.path.join(scratch, 'from_sbsar'),
                'graph': TEST_GRAPH,
                'output_format': 'tga',
            },
        )
    )
    check('render_sbs', 'from a .sbsar, graph, tga', re.search(r'height\.tga  \d+x\d+', t) is not None, t)
    # cooking drops the graph's default parent size: a .sbsar keeps 256 px, and says so
    check(
        'render_sbs',
        '.sbsar: own default size, stated',
        'height.tga  256x256' in t and "the .sbsar's own default, 256 px" in t,
        t,
    )
    t = text(
        await c(
            'render_sbs', {'sbs_path': sbsar, 'output_dir': os.path.join(scratch, 'from_sbsar_512'), 'size_log2': 9}
        )
    )
    check('render_sbs', '.sbsar with size_log2', 'height.png  512x512' in t, t.splitlines()[-1])
    r_ = await c(
        'render_sbs', {'sbs_path': sbsar, 'output_dir': os.path.join(scratch, 'nope'), 'graph': 'no_such_graph'}
    )
    check('render_sbs', 'error on unknown graph', r_.is_error and 'no_such_graph' in text(r_), text(r_)[:150])
    # a ready-made material from a subfolder of the library, in a graph of its own (ROADMAP item 41): added by its
    # path, computed in Designer, saved, and cooked, since the saved file refers to it as sbs://materials/pbr/...
    mat = {'graph': TEST_GRAPH + '_material'}
    mat_sbs = os.path.join(scratch, 'uses_material.sbs')
    await c('create_graph', {'name': mat['graph'], 'save_path': mat_sbs, 'size_log2': 8})
    t = text(
        await c(
            'apply_edits',
            {
                'ops': [
                    {'op': 'add', 'definition': 'materials/pbr/bricks_001', 'ref': 'm'},
                    {'op': 'add', 'definition': 'output', 'ref': 'o', 'position': [300, 0]},
                    {'op': 'connect', 'from': 'm', 'output': 'basecolor', 'to': 'o', 'input': 'inputNodeOutput'},
                ],
                **mat,
            },
        )
    )
    check(
        'apply_edits',
        'add: a material in a subfolder, its basecolor wired',
        'instance:bricks_001' in t
        and 'applied 3 op' in t
        and 'basecolor' in t.split('applied 3 op')[0].splitlines()[-1],
        t,
    )
    t = text(await c('export_outputs', {'output_dir': os.path.join(scratch, 'material'), **mat}))
    check('export_outputs', 'a material in a subfolder computes', 'exported 1 file(s)' in t, t)
    await c('save_package', {'graph_or_path': mat_sbs})
    with open(mat_sbs, encoding='utf-8') as mat_file:
        saved = mat_file.read()
    t = text(await c('render_sbs', {'sbs_path': mat_sbs, 'output_dir': os.path.join(scratch, 'material_render')}))
    check(
        'render_sbs',
        'a material in a subfolder cooks and renders',
        'sbs://materials/pbr/bricks_001.sbs' in saved and '.png' in t and 'ERROR' not in t,
        t[-300:],
    )
    # and it shows something: a real material isn't one flat colour
    rendered_material = np.array(Image.open(os.path.join(scratch, 'material_render', 'output.png'))).astype(float)
    check(
        'render_sbs',
        'a material in a subfolder renders an image with detail',
        rendered_material[..., :3].std() > 1,
        str(rendered_material[..., :3].std()),
    )
    # a material's first output is `diffuse`, off by default and black on a metal, so a tool picking the first says so
    # (REVIEW.md HLP-65). GUIDE.md's library facts rely on these
    t = text(
        await c(
            'apply_edits',
            {
                'ops': [
                    {'op': 'add', 'definition': 'materials/pbr/metal_003', 'ref': 'metal'},
                    {'op': 'add', 'definition': 'output', 'ref': 'o2', 'position': [300, 300]},
                    {'op': 'connect', 'from': 'metal', 'to': 'o2', 'input': 'inputNodeOutput'},
                ],
                **mat,
            },
        )
    )
    metal = re.search(r"ref 'metal' = (\d+)", t)
    output2 = re.search(r"ref 'o2' = (\d+)", t)
    check(
        'apply_edits',
        'connect takes the output tagged base colour, and says so',
        '.basecolor' in t and 'tagged base colour, of 9' in t,
        t[-300:],
    )
    metal_id = metal.group(1) if metal else ''
    r_ = await c('preview_node', {'node_id': metal_id, 'max_size': 64, **mat})
    check(
        'preview_node',
        'says which output it took',
        is_image(r_) and "'basecolor', tagged base colour, of 9" in text(r_),
        text(r_)[:200],
    )
    r_ = await c('preview_node', {'node_id': metal_id, 'output': 'basecolor', 'max_size': 64, **mat})
    check(
        'preview_node',
        'says nothing when told the output',
        is_image(r_) and 'no output given' not in text(r_),
        text(r_)[:200],
    )
    diffuse = text(await c('node_stats', {'node_id': metal_id, 'output': 'diffuse', **mat}))
    basecolor = text(await c('node_stats', {'node_id': metal_id, 'output': 'basecolor', **mat}))
    metal_means = [re.findall(r'mean[ =:]*([0-9.]+)', stats) for stats in (diffuse, basecolor)]
    check(
        'designer facts',
        "a metal's diffuse map is black, its basecolor isn't",
        bool(metal_means[0])
        and bool(metal_means[1])
        and max(map(float, metal_means[0][:3])) < 0.01
        and max(map(float, metal_means[1][:3])) > 0.3,
        diffuse[:150] + ' | ' + basecolor[:150],
    )
    t = text(await c('describe_node', {'definition': 'materials/pbr/metal_003'}))
    check(
        'designer facts',
        "a material's normal_format defaults to DirectX",
        re.search(r'normal_format\b.*\n.*0;|DirectX=0', t) is not None and 'OpenGL=1' in t,
        '\n'.join(l for l in t.splitlines() if 'irectX' in l or 'normal_format' in l)[:300],
    )
    # a sweep names the output it looks at (the normal map moves, the diffuse doesn't)
    r_ = await c(
        'sweep_param', {'node_id': metal_id, 'param': 'normal_intensity', 'values': [1], 'tile_size': 64, **mat}
    )
    check('sweep_param', 'says which output it took', 'tagged base colour, of 9' in text(r_), text(r_)[:250])
    # the tools that measure carry the same note, and measure the tagged map: not a black one (HLP-66)
    t = text(await c('node_stats', {'node_id': metal_id, **mat}))
    check(
        'node_stats',
        'with no output, the tagged map, and says so',
        'tagged base colour' in t and '.basecolor' in t,
        t[:200],
    )
    t = text(await c('check_tiling', {'node_id': metal_id, 'axis': 'horizontal', **mat}))
    check(
        'check_tiling',
        'with no output, the tagged map, and says so',
        'tagged base colour' in t and '.basecolor' in t,
        t[:200],
    )
    # diff_graph names a rewired output (REVIEW.md SRV-59)
    await c('save_package', {'graph_or_path': mat_sbs})
    await c(
        'apply_edits',
        {
            'ops': [
                {
                    'op': 'connect',
                    'from': metal_id,
                    'output': 'metallic',
                    'to': output2.group(1) if output2 else '',
                    'input': 'inputNodeOutput',
                }
            ],
            **mat,
        },
    )
    t = text(await c('diff_graph', mat))
    check('diff_graph', 'names a rewired output', '.metallic added' in t and '.basecolor removed' in t, t)
    # a custom package: its own name for the map, tagged by the user (not Designer's name, not its first output).
    # Two unsaved packages of their own, unloaded here and never saved: saving a graph that uses an unsaved package
    # makes Designer ask where to save it, in a dialog on the user's screen (REVIEW.md SRV-60)
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': helpers_source()
                + (
                    dedent("""
                        from sd.api.sdvaluearray import SDValueArray
                        from sd.api.sdvaluestring import SDValueString
                        from sd.api.sdvalueusage import SDValueUsage
                        from sd.api.sdusage import SDUsage
                        from sd.api.sdtypeusage import SDTypeUsage
                        custom = SDSBSCompGraph.sNew(_PM.newUserPackage())
                        custom.setIdentifier('mcp_selftest_custom')
                        for ident, tag in (('mask', None), ('albedo', 'baseColor')):
                            o = custom.newNode('sbs::compositing::output')
                            o.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew(ident))
                            if tag:
                                tags = SDValueArray.sNew(SDTypeUsage.sNew(), 0)
                                tags.pushBack(SDValueUsage.sNew(SDUsage.sNew(tag, 'RGBA', 'sRGB')))
                                o.setAnnotationPropertyValueFromId('usages', tags)
                        host = SDSBSCompGraph.sNew(_PM.newUserPackage())
                        host.setIdentifier('mcp_selftest_custom_host')
                        n = host.newInstanceNode(custom)
                        outs = [p.getId() for p in n.getProperties(SDPropertyCategory.Output)]
                        try:
                            print('CUSTOM=' + _output_note(_default_output(n, outs)[1]))
                        finally:
                            for g in (host, custom):
                                _PM.unloadUserPackage(g.getPackage())
                    """)
                )
            },
        )
    )
    check(
        'designer facts',
        "a custom package's tagged output is taken",
        "CUSTOM=no output given: 'albedo', tagged base colour, of 2" in t,
        t[-250:],
    )
    r_ = await c('preview_maps', {'map_dir': os.path.join(scratch, 'export')})
    check('preview_maps', 'all maps in a folder', is_image(r_), '' if is_image(r_) else text(r_))
    r_ = await c('preview_maps', {'map_dir': render_dir, 'names': ['height'], 'tile_size': 256})
    check('preview_maps', 'side by side', is_image(r_), '')
    r_ = await c('preview_maps', {'map_dir': render_dir, 'names': ['height'], 'crop': [0, 0, 128, 128]})
    check('preview_maps', 'crop', is_image(r_), '')
