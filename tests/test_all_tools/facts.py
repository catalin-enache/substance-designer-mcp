"""Designer facts AGENTS.md relies on (they fail if a Designer update changes them)."""

import base64
import os
import re
import tempfile

from .common import FACTS, GRAPH_OF, TEST_GRAPH, Ctx, added_id, check, is_image, pixel_values, skip, text


async def run(ctx: Ctx) -> None:
    c, scratch, G, slope, lv, png = ctx.c, ctx.scratch, ctx.G, ctx.slope, ctx.lv, ctx.png
    # --- Designer facts that AGENTS.md relies on (fail if a Designer update changes them)
    F = 'designer facts'
    t = text(await c('describe_node', {'definition': 'blend'}))
    check(
        F,
        'blend mode ids',
        'copy=0, add=1, substract=2, multiply=3, addsub=4, max=5, min=6, '
        'switch=7, divide=8, overlay=9, screen=10, softlight=11' in t,
        '',
    )
    check(
        F,
        '$format ids',
        '8_bits_per_channel=0, 16_bits_per_channel=1, hdr_low_precision=2, hdr_high_precision=3' in t,
        '',
    )
    for definition, ins, outs in [
        ('bevel', ['input'], ['height', 'normal']),
        ('tile_generator', [], ['TileGenerator']),
        ('hbao', ['input'], ['output']),
        ('curvature_smooth', ['input'], ['height']),
    ]:
        t = text(await c('describe_node', {'definition': definition}))
        out_line = re.search(r'output connector ids: (.*)', t)
        ok = (
            out_line is not None
            and all("'%s'" % o in out_line.group(1) for o in outs)
            and all(re.search(r'^\s+%s\s+CONNECTOR' % i, t, re.M) for i in ins)
        )
        check(F, '%s connectors' % definition, ok, out_line.group(0) if out_line else t[:150])
    t = text(await c('execute_designer_code', {'code': FACTS % (TEST_GRAPH, lv, lv, slope)}))
    check(F, '29 atomic nodes', 'ATOMIC=29' in t, t)
    check(F, 'APIException is not an Exception', 'APIEXC_BASE_ONLY=True' in t, t)
    check(F, 'connections reported from queried side', 'QUERIED_SIDE=True' in t, t)
    # how a .sbs stores size inheritance (server._RELATIVE_TO): measure it
    inherit_dir = os.path.join(scratch, 'inherit')
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': (
                    'import sd, os\nfrom sd.api.sbs.sdsbscompgraph import SDSBSCompGraph\n'
                    'from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod as M\n'
                    'pm=sd.getContext().getSDApplication().getPackageMgr()\nos.makedirs(%r, exist_ok=True)\n'
                    'for m in (M.Absolute, M.RelativeToInput, M.RelativeToParent):\n'
                    "    pkg=pm.newUserPackage(); g=SDSBSCompGraph.sNew(pkg); g.setIdentifier('mcp_selftest_inherit_'+m.name)\n"
                    "    n=g.newNode('sbs::compositing::blur')\n"
                    "    g.setPropertyInheritanceMethod(g.getPropertyFromId('$outputsize', SDPropertyCategory.Input), m)\n"
                    "    n.setPropertyInheritanceMethod(n.getPropertyFromId('$outputsize', SDPropertyCategory.Input), m)\n"
                    "    pm.savePackageAs(pkg, os.path.join(%r, m.name + '.sbs')); pm.unloadUserPackage(pkg)\n"
                    "print('saved')"
                )
                % (inherit_dir, inherit_dir)
            },
        )
    )
    stored = {}
    for name in ('Absolute', 'RelativeToInput', 'RelativeToParent'):
        import xml.etree.ElementTree as ET

        g_el = next(ET.parse(os.path.join(inherit_dir, name + '.sbs')).getroot().iter('graph'))
        # a missing element raises AttributeError, reported by the run's except (TST-63)
        graph_rel = [p.find('relativeTo').get('v') for p in g_el.find('baseParameters') or []]  # type: ignore[union-attr]
        node_rel = [
            p.find('relativeTo').get('v')  # type: ignore[union-attr]
            for p in g_el.iter('parameter')
            if p.find('name').get('v') == 'outputsize'  # type: ignore[union-attr]
            and p not in list(g_el.find('baseParameters') or [])
        ]
        stored[name] = (graph_rel, node_rel)
    check(
        F,
        '.sbs size inheritance: 0 absolute, 1 parent, 2 input, defaults unstored',
        stored == {'Absolute': (['0'], ['0']), 'RelativeToInput': (['2'], []), 'RelativeToParent': ([], ['1'])},
        str(stored),
    )
    # REVIEW.md TST-3: the remaining AGENTS.md facts, measured
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': (
                    'from sd.api.sdproperty import SDPropertyInheritanceMethod as M\n'
                    "print('API_INHERIT=%d,%d,%d' % (M.RelativeToInput.value, M.RelativeToParent.value, M.Absolute.value))"
                )
            },
        )
    )
    check(F, 'API inheritance: RelativeToInput 0, RelativeToParent 1, Absolute 2', 'API_INHERIT=0,1,2' in t, t)
    # two unsaved packages copy the same file, one after the other: AGENTS.md says the copy
    # goes to <OS temp>/Adobe/Adobe Substance 3D Designer/ with an XXXXXX- prefix, stays
    # after its package closes, and so the next copy of that name gets 1- in front
    # (REVIEW.md TST-15: the check used to test only "under the temp folder")
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': (
                    'import os, sd\nfrom sd.api.sbs.sdsbscompgraph import SDSBSCompGraph\n'
                    'from sd.api.sdresourcebitmap import SDResourceBitmap\nfrom sd.api.sdresource import EmbedMethod\n'
                    'pm=sd.getContext().getSDApplication().getPackageMgr()\n'
                    'for i in range(2):\n'
                    '    pkg=pm.newUserPackage()\n'
                    "    SDSBSCompGraph.sNew(pkg).setIdentifier('mcp_selftest_unsaved_copy')\n"
                    '    res=SDResourceBitmap.sNewFromFile(pkg, %r, EmbedMethod.CopiedAndLinked)\n'
                    '    path=res.getFilePath()\n    pm.unloadUserPackage(pkg)\n'
                    "    print('COPY=%%s STAYS=%%s' %% (path, os.path.isfile(path)))"
                )
                % png
            },
        )
    )
    copies = re.findall(r'COPY=(.*) STAYS=(\w+)', t)
    names = [os.path.basename(p) for p, _ in copies]
    folders = {os.path.normcase(os.path.realpath(os.path.dirname(p))) for p, _ in copies}
    expected_folder = os.path.normcase(
        os.path.realpath(os.path.join(tempfile.gettempdir(), 'Adobe', 'Adobe Substance 3D Designer'))
    )
    check(
        F,
        'CopiedAndLinked before the first save: XXXXXX- copy in <OS temp>/Adobe/Adobe Substance 3D '
        'Designer/, kept after closing, the next one numbered',
        len(copies) == 2
        and all(stays == 'True' for _, stays in copies)
        and folders == {expected_folder}
        and names[0].endswith('XXXXXX-' + os.path.basename(png))
        and names[1] != names[0]
        and re.match(r'^\d+-%s$' % re.escape(re.sub(r'^\d+-', '', names[0])), names[1]) is not None,
        t.strip(),
    )
    for copy_path, _ in copies:
        if os.path.isfile(copy_path) and 'XXXXXX-' in os.path.basename(copy_path):
            os.remove(copy_path)  # Designer leaves them there
    t = text(await c('describe_node', {'definition': 'tile_generator'}))
    ids_ok = all(
        re.search(r'^\s+%s\s' % re.escape(i), t, re.M)
        for i in (
            'Nb_X',
            'Nb_Y',
            'Pattern_Type',
            'Scale',
            'Offset',
            'Offset_Random',
            'Offset_Random_Seed',
            'Free_Rotation',
            'Luminance_Variation-Contrast',
        )
    )
    pattern = re.search(r'^\s+Pattern_Type\s.*default=(\d+)\n\s+enum: (.*)$', t, re.M)
    check(
        F,
        'tile_generator ids; Pattern_Type 1 image input, 2 square, 9 brick (default)',
        ids_ok
        and pattern is not None
        and pattern.group(1) == '9'
        and 'Image input=1, Square=2' in pattern.group(2)
        and 'Brick=9' in pattern.group(2),
        pattern.group(0).strip()[:150] if pattern else 'Pattern_Type not found',
    )
    aniso = added_id(text(await c('add_node', {'definition': 'noise_anisotropic_noise.sbs/anisotropic_noise', **G})))
    r_ = await c('preview_node', {'node_id': aniso, 'max_size': 256, **G})
    if is_image(r_):
        import io as _io

        import numpy as np
        from PIL import Image as PILImage

        img = next(x for x in r_.content if x.type == 'image')
        a_ = np.asarray(PILImage.open(_io.BytesIO(base64.b64decode(img.data))).convert('L'), dtype=float)
        along_x, along_y = np.abs(np.diff(a_, axis=1)).mean(), np.abs(np.diff(a_, axis=0)).mean()
        check(
            F,
            'anisotropic noise streaks run horizontally by default',
            along_y > 2 * along_x,
            'mean step along x %.2f, along y %.2f' % (along_x, along_y),
        )
    else:
        check(F, 'anisotropic noise streaks run horizontally by default', False, text(r_))
    await c('delete_nodes', {'node_ids': [aniso], **G})
    # exposing a parameter logs these until the function node is named: count each
    # message before and after an exposure made here, so earlier lines can't satisfy the
    # check (REVIEW.md TST-13: it once compared against a header it could never match)
    noise = ('No output node defined', "nodes don't have a variable name")  # logged as "Some <b>Get</b> nodes ..."

    async def noise_counts() -> list[int]:
        found: list[int] = []
        for message in noise:
            header = text(await c('read_designer_log', {'contains': message, 'lines': 1})).splitlines()[0]
            # no match raises AttributeError, which the run's except reports (REVIEW.md TST-63)
            found.append(int(re.search(r'\((\d+) matching line', header).group(1)))  # type: ignore[union-attr]
        return found

    before = await noise_counts()
    log_lv = added_id(text(await c('add_node', {'definition': 'levels', **G})))
    await c('expose_param', {'node_id': log_lv, 'param': 'levelinlow', 'input_id': 'log_noise_check', **G})
    after = await noise_counts()
    await c('remove_graph_input', {'input_id': 'log_noise_check', **G})
    await c('delete_nodes', {'node_ids': [log_lv], **G})
    check(
        F,
        'exposing an input logs the documented harmless messages',
        all(b > a for a, b in zip(before, after, strict=False)),
        'counts before %s, after %s' % (before, after),
    )
    # widget capture can't see the GPU-drawn 3D render: a grab of its viewport (leftover
    # content that changes from call to call) is clearly unlike the view's own render
    grab_png = os.path.join(scratch, 'grab3d.png')
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': (
                    'import sd\nfrom PySide6.QtWidgets import QDockWidget, QWidget\n'
                    'mw=sd.getContext().getSDApplication().getQtForPythonUIMgr().getMainWindow()\n'
                    "d=[d for d in mw.findChildren(QDockWidget) if d.objectName().startswith('areaD_') and d.isVisible()]\n"
                    "vp=[w for w in d[0].findChildren(QWidget) if w.metaObject().className()=='Alg::Gui3D::ViewportWidget'] if d else []\n"
                    "print('NO_3D_VIEW' if not vp else 'SAVED=%%s' %% vp[0].grab().save(%r))"
                )
                % grab_png
            },
        )
    )
    render = await c('screenshot_designer', {'panel': '3d', 'max_size': 128})
    if 'NO_3D_VIEW' in t or not is_image(render):
        skip(F, 'widget capture of the 3D view is not the render', 'no 3D View visible in Designer')
    else:
        import io as _io

        import numpy as np
        from PIL import Image as PILImage

        shot = PILImage.open(_io.BytesIO(base64.b64decode(next(x for x in render.content if x.type == 'image').data)))
        size = (64, 40)
        a_ = np.asarray(shot.convert('L').resize(size), dtype=float)
        b_ = np.asarray(PILImage.open(grab_png).convert('L').resize(size), dtype=float)
        diff = float(np.abs(a_ - b_).mean())
        check(
            F,
            'widget capture of the 3D view is not the render',
            diff > 20,
            'mean difference %.1f of 255 between the grab and the render' % diff,
        )
    t = text(
        await c(
            'execute_designer_code',
            {
                'code': GRAPH_OF % TEST_GRAPH
                + (
                    'from sd.api.sdresourcebitmap import SDResourceBitmap\nfrom sd.api.sdresource import EmbedMethod\n'
                    'from sd.api.apiexception import APIException\n'
                    "try:\n    SDResourceBitmap.sNewFromFile(g.getPackage(), %r, EmbedMethod.BinaryEmbedded); print('EMBED=ok')\n"
                    "except APIException as e:\n    print('EMBED=' + str(e))\n"
                    'from sd.api.sdbasetypes import int2\nsaved=g.getDefaultParentSize()\n'
                    "g.setDefaultParentSize(int2(256, 256)); print('PARENT=%%d' %% g.getDefaultParentSize().x)\n"
                    'g.setDefaultParentSize(saved)'
                )
                % png
            },
        )
    )
    check(F, 'bitmaps cannot be embedded (NotSupported)', 'EMBED=SDApiError.NotSupported' in t, t)
    check(F, 'setDefaultParentSize takes pixels, not log2', 'PARENT=256' in t, t)
    grad = added_id(text(await c('add_node', {'definition': 'gradient_linear_1', 'position': [-600, 600], **G})))
    nrm = added_id(
        text(
            await c(
                'add_node',
                {'definition': 'normal', 'position': [-400, 600], 'params': {'intensity': 5.0, 'inversedy': True}, **G},
            )
        )
    )
    await c('connect', {'from_node': grad, 'to_node': nrm, 'to_input': 'input1', **G})
    px = pixel_values(
        text(await c('node_stats', {'node_id': grad, 'points': [[0, 0], [511, 0], [0, 511], [300, 511]], **G}))
    )
    check(
        F,
        'gradient_linear_1: 1 at top, 0 at bottom',
        min(px[(0, 0)][0], px[(511, 0)][0]) > 0.99 and max(px[(0, 511)][0], px[(300, 511)][0]) < 0.01,
        str(px),
    )
    # height rises towards the top: OpenGL (Y up) normals lean down there, so green < 0.5
    gl = pixel_values(text(await c('node_stats', {'node_id': nrm, 'points': [[256, 256]], **G})))[(256, 256)]
    await c('set_params', {'node_id': nrm, 'params': {'inversedy': False}, **G})
    dx = pixel_values(text(await c('node_stats', {'node_id': nrm, 'points': [[256, 256]], **G})))[(256, 256)]
    # a full-height ramp is a gentle slope (G about 0.49 vs 0.51); the sign is what matters
    check(
        F,
        'normal inversedy=True is OpenGL',
        gl[1] < 0.497 and dx[1] > 0.503 and abs(gl[1] + dx[1] - 1) < 0.002,
        'OpenGL G=%.3f, DirectX G=%.3f' % (gl[1], dx[1]),
    )
    await c('delete_nodes', {'node_ids': [grad, nrm], **G})
