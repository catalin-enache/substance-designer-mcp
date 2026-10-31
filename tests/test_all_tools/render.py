"""Output: export_outputs, sbsar_info, render_sbs (seeds, sizes, formats) and preview_maps."""

import os
import re
import subprocess
import sys
from typing import Any

from .common import BUNDLE, GRAPH_OF, TEST_GRAPH, Ctx, _mean_png, check, is_image, text


async def run(ctx: Ctx) -> None:
    c, scratch, G, clouds, sbs = ctx.c, ctx.scratch, ctx.G, ctx.clouds, ctx.sbs
    t = text(await c('export_outputs', {'graph': TEST_GRAPH, 'output_dir': os.path.join(scratch, 'export')}))
    check('export_outputs', 'from Designer', 'height.png  512x512' in t, t)
    t = text(await c('sbsar_info', {'sbs_path': sbs}))
    check('sbsar_info', 'graph + output', 'pkg://%s' % TEST_GRAPH in t and 'OUTPUT height' in t, t.splitlines()[0])
    # the graph seed set with a set op is still a control of the cooked graph (REVIEW.md HLP-25)
    check(
        'sbsar_info',
        'the graph seed set with a set op is still exposed',
        'INPUT $randomseed' in t,
        ' / '.join(l for l in t.splitlines() if 'INPUT' in l),
    )
    # and an Absolute one is not (AGENTS.md): a copy saved with it Absolute, the graph put back;
    # changing the inheritance resets the value, so the value goes back after it
    abs_sbs = os.path.join(scratch, 'seed_absolute.sbs')
    await c(
        'execute_designer_code',
        {
            'code': GRAPH_OF % TEST_GRAPH
            + (
                'from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n'
                'from sd.api.sdvalueint import SDValueInt\n'
                "p = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\nkept = g.getPropertyValue(p).get()\n"
                'g.setPropertyInheritanceMethod(p, IM.Absolute)\n'
                'try:\n    sd.getContext().getSDApplication().getPackageMgr().saveCopyOfPackageAs(g.getPackage(), %r)\n'
                'finally:\n    g.setPropertyInheritanceMethod(p, IM.RelativeToParent)\n'
                '    g.setPropertyValue(p, SDValueInt.sNew(kept))'
            )
            % abs_sbs
        },
    )
    t_abs = text(await c('sbsar_info', {'sbs_path': abs_sbs}))
    check(
        'designer facts',
        'an Absolute graph $randomseed is not exposed in a .sbsar (AGENTS.md)',
        'INPUT $outputsize' in t_abs and 'INPUT $randomseed' not in t_abs,
        ' / '.join(l for l in t_abs.splitlines() if 'INPUT' in l),
    )
    # the stored seed (5) reaches the .sbsar too, added to the seed a render sets (AGENTS.md: "its
    # value is added to its parent's seed"; REVIEW.md TST-39, TST-44): copies storing 0 and 3 to compare
    seed_copies = {}
    for stored_seed in (0, 3):  # copies of the graph storing another seed
        seed_copies[stored_seed] = os.path.join(scratch, 'seed_stored%d.sbs' % stored_seed)
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + (
                    'from sd.api.sdproperty import SDPropertyCategory\nfrom sd.api.sdvalueint import SDValueInt\n'
                    "p = g.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                    'kept = g.getPropertyValue(p).get()\n'
                    'g.setPropertyValue(p, SDValueInt.sNew(%d))\n'
                    'try:\n    sd.getContext().getSDApplication().getPackageMgr().saveCopyOfPackageAs(g.getPackage(), %r)\n'
                    'finally:\n    g.setPropertyValue(p, SDValueInt.sNew(kept))'
                )
                % (stored_seed, seed_copies[stored_seed])
            },
        )
    zero_sbs = seed_copies[0]
    # and one with the clouds node's seed made Absolute (REVIEW.md TST-52); the graph's untouched
    abs_node_sbs = os.path.join(scratch, 'seed_absolute_node.sbs')
    await c(
        'execute_designer_code',
        {
            'code': GRAPH_OF % TEST_GRAPH
            + (
                'from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as IM\n'
                'from sd.api.sdvalueint import SDValueInt\n'
                "n = g.getNodeFromId('%s'); p = n.getPropertyFromId('$randomseed', SDPropertyCategory.Input)\n"
                'was, kept = n.getPropertyInheritanceMethod(p), n.getPropertyValue(p).get()\n'
                'try:\n    n.setPropertyInheritanceMethod(p, IM.Absolute)\n'
                '    sd.getContext().getSDApplication().getPackageMgr().saveCopyOfPackageAs(g.getPackage(), %r)\n'
                'finally:\n    n.setPropertyInheritanceMethod(p, was); n.setPropertyValue(p, SDValueInt.sNew(kept))'
            )
            % (clouds, abs_node_sbs)
        },
    )
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
        'an inherited graph seed stored in the .sbsar is added to the render seed (AGENTS.md)',
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
        "a node $randomseed made Absolute ignores the render's seed (AGENTS.md)",
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
    # the same to within a few 16-bit steps at a few pixels (AGENTS.md, Output; seen: 27 of
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
    twin = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + (
                    'from sd.api.sdvaluestring import SDValueString\n'
                    "o = g.newNode('sbs::compositing::output')\n"
                    "o.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew('Height'))\n"
                    "print('TWIN=' + o.getIdentifier())"
                )
            },
        )
    )
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
    r_ = await c('preview_maps', {'map_dir': os.path.join(scratch, 'export')})
    check('preview_maps', 'all maps in a folder', is_image(r_), '' if is_image(r_) else text(r_))
    r_ = await c('preview_maps', {'map_dir': render_dir, 'names': ['height'], 'tile_size': 256})
    check('preview_maps', 'side by side', is_image(r_), '')
    r_ = await c('preview_maps', {'map_dir': render_dir, 'names': ['height'], 'crop': [0, 0, 128, 128]})
    check('preview_maps', 'crop', is_image(r_), '')
