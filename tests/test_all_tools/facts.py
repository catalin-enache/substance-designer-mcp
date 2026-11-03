"""Designer facts AGENTS.md relies on (they fail if a Designer update changes them)."""

import base64
import os
import re
import tempfile
from textwrap import dedent
from typing import cast

from .common import (
    TEST_GRAPH,
    Ctx,
    added_id,
    check,
    designer_script,
    is_image,
    pixel_values,
    skip,
    text,
)


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
    t = text(await designer_script(c, 'facts/api_basics', graph=TEST_GRAPH, node=lv, source=slope))
    check(F, '29 atomic nodes', 'ATOMIC=29' in t, t)
    check(F, 'APIException is not an Exception', 'APIEXC_BASE_ONLY=True' in t, t)
    check(F, 'connections reported from queried side', 'QUERIED_SIDE=True' in t, t)
    # the table in AGENTS.md: what a function graph on a parameter does, per state. The stored value
    # is 0.5 before any function graph, the function reads an input at 0.25, expose adds a second at 0.75
    t = text(await designer_script(c, 'facts/function_states'))
    for state, cells in (
        (
            'none',
            'stored 0.50, output 0.50 | set: function none, output 0.60 '
            '| expose: function 1 nodes 1 outputs, output 0.75 | delete: stored 0.50, output 0.50',
        ),
        (
            'empty',
            'stored 1.00, output 1.00 | set: function none, output 0.60 '
            '| expose: function 1 nodes 1 outputs, output 0.75 | delete: stored 1.00, output 1.00',
        ),
        (
            'no-output',
            'stored 1.00, output 1.00 | set: function none, output 0.60 '
            '| expose: function 2 nodes 1 outputs, output 0.75 | delete: stored 1.00, output 1.00',
        ),
        (
            'output',
            'stored 1.00, output 0.25 | set: function none, output 0.60 '
            '| expose: function 2 nodes 1 outputs, output 0.75 | delete: stored 1.00, output 1.00',
        ),
    ):
        check(F, 'function graph on a parameter, state %s' % state, '%s | %s' % (state, cells) in t, t)
    check(
        F,
        'an unconnected get node has no effect; removing an input a connected one reads changes the output',
        'unconnected get | output 0.25, its input changed 0.25, the connected input removed 1.00' in t,
        t,
    )
    check(
        F,
        'a function graph keeps its output node, or lack of one, after a reload',
        'reloaded | 1 nodes 1 outputs | 1 nodes 0 outputs' in t,
        t,
    )
    # the table on other kinds of parameter: an enum's and an instance node's follow it, $outputsize doesn't
    for row in (
        'enum none | output 1.00 | set: function none, output 0.50 | delete: output 1.00',
        'enum empty | output 0.50 | set: function none, output 0.50 | delete: output 0.50',
        'enum no-output | output 0.50 | set: function none, output 0.50 | delete: output 0.50',
        'enum output | output 0.25 | set: function none, output 0.50 | delete: output 0.50',
        'instance none | output 0.50 | set: function none, output 0.60 | delete: output 0.50',
        'instance empty | output 1.00 | set: function none, output 0.60 | delete: output 1.00',
        'instance no-output | output 1.00 | set: function none, output 0.60 | delete: output 1.00',
        'instance output | output 0.25 | set: function none, output 0.60 | delete: output 1.00',
        '$outputsize Absolute none | Absolute, stored 5,5, 32 px | delete: Absolute',
        '$outputsize Absolute empty | Absolute, stored 8,8, 16 px | delete: RelativeToInput',
        '$outputsize Absolute no-output | Absolute, stored 8,8, 16 px | delete: RelativeToInput',
        '$outputsize Absolute output | Absolute, stored 8,8, 8 px | delete: RelativeToInput',
        '$outputsize RelativeToParent none | RelativeToParent, stored 5,5, 512 px | delete: RelativeToParent',
        '$outputsize RelativeToParent empty | RelativeToParent, stored 0,0, 16 px | delete: RelativeToInput',
        '$outputsize RelativeToParent no-output | RelativeToParent, stored 0,0, 16 px | delete: RelativeToInput',
        '$outputsize RelativeToParent output | RelativeToParent, stored 0,0, 128 px | delete: RelativeToInput',
        '$format on levels: delete: Absolute -> RelativeToInput, RelativeToParent -> RelativeToInput',
        '$tiling on levels: delete: Absolute -> RelativeToInput, RelativeToParent -> RelativeToInput',
        '$pixelratio on levels: delete: Absolute -> RelativeToInput, RelativeToParent -> RelativeToInput',
        '$pixelsize on levels: delete: Absolute -> RelativeToInput, RelativeToParent -> RelativeToInput',
        '$randomseed on levels: delete: Absolute -> RelativeToInput, RelativeToParent -> RelativeToInput',
        '$outputsize on instance: delete: Absolute -> RelativeToParent, RelativeToParent -> RelativeToParent',
    ):
        check(F, 'function graph: %s' % row, row in t, t)
    check(
        F,
        "an FX-Map's function reads the input, and removing it changes the output",
        'fx-map | input at 0.25 0.25 | at 0.75 0.75 | removed 1.00' in t,
        t,
    )
    # a graph's model is the same through a save and a reload, so a diff against a saved file reports no change
    # (REVIEW.md SRV-70)
    first, second = os.path.join(scratch, 'round_trip_1.sbs'), os.path.join(scratch, 'round_trip_2.sbs')
    await designer_script(c, 'facts/save_round_trip', graph=TEST_GRAPH, first=first, second=second)
    from server_tools.snapshots import _graph_model

    one, two = _graph_model(first, TEST_GRAPH), _graph_model(second, TEST_GRAPH)
    differing = [key for key in one if one[key] != two[key]]  # type: ignore[literal-required]
    nodes = [
        (node, field, one['nodes'][node][field], two['nodes'][node][field])  # type: ignore[literal-required]
        for node in one['nodes']
        if node in two['nodes']
        for field in one['nodes'][node]
        if one['nodes'][node][field] != two['nodes'][node][field]  # type: ignore[literal-required]
    ]
    check(F, "a graph's model is the same after a save and a reload", not differing, '%s %s' % (differing, nodes[:2]))
    # an int on an enum parameter is accepted whatever it is, and one beyond the enum's can't be read back: why
    # remove_graph_input checks first (AGENTS.md; REVIEW.md HLP-73)
    t = text(await designer_script(c, 'facts/enum_int_beyond_values'))
    check(
        F,
        "an int beyond an enum's values is accepted and can't be read back",
        'ENUM_5=5' in t and 'ACCEPTED_99' in t and 'READ_99_RAISES' in t,
        t,
    )
    # how a .sbs stores size inheritance (server._RELATIVE_TO): measure it
    inherit_dir = os.path.join(scratch, 'inherit')
    t = text(await designer_script(c, 'facts/size_inheritance_files', folder=inherit_dir))
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
                'code': dedent("""\
                    from sd.api.sdproperty import SDPropertyInheritanceMethod as M
                    print('API_INHERIT=%d,%d,%d' % (M.RelativeToInput.value, M.RelativeToParent.value, M.Absolute.value))""")
            },
        )
    )
    check(F, 'API inheritance: RelativeToInput 0, RelativeToParent 1, Absolute 2', 'API_INHERIT=0,1,2' in t, t)
    # two unsaved packages copy the same file, one after the other: AGENTS.md says the copy
    # goes to <OS temp>/Adobe/Adobe Substance 3D Designer/ with an XXXXXX- prefix, stays
    # after its package closes, and so the next copy of that name gets 1- in front
    # (REVIEW.md TST-15: the check used to test only "under the temp folder")
    t = text(await designer_script(c, 'facts/unsaved_bitmap_copies', png=png))
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
    aniso = added_id(
        text(
            await c(
                'apply_edits',
                {'ops': [{'op': 'add', 'definition': 'noise_anisotropic_noise.sbs/anisotropic_noise'}], **G},
            )
        )
    )
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
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': aniso}], **G})
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
    log_lv = added_id(text(await c('apply_edits', {'ops': [{'op': 'add', 'definition': 'levels'}], **G})))
    await c(
        'apply_edits',
        {'ops': [{'op': 'expose', 'node': log_lv, 'param': 'levelinlow', 'input_id': 'log_noise_check'}], **G},
    )
    after = await noise_counts()
    await c('remove_graph_input', {'input_id': 'log_noise_check', **G})
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': log_lv}], **G})
    check(
        F,
        'exposing an input logs the documented harmless messages',
        all(b > a for a, b in zip(before, after, strict=False)),
        'counts before %s, after %s' % (before, after),
    )
    # widget capture can't see the GPU-drawn 3D render: a grab of its viewport (leftover
    # content that changes from call to call) is clearly unlike the view's own render
    grab_png = os.path.join(scratch, 'grab3d.png')
    t = text(await designer_script(c, 'facts/grab_3d_view', path=grab_png))
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
    t = text(await designer_script(c, 'facts/embed_and_parent_size', graph=TEST_GRAPH, png=png))
    check(F, 'bitmaps cannot be embedded (NotSupported)', 'EMBED=SDApiError.NotSupported' in t, t)
    check(F, 'setDefaultParentSize takes pixels, not log2', 'PARENT=256' in t, t)
    grad = added_id(
        text(
            await c(
                'apply_edits', {'ops': [{'op': 'add', 'definition': 'gradient_linear_1', 'position': [-600, 600]}], **G}
            )
        )
    )
    nrm = added_id(
        text(
            await c(
                'apply_edits',
                {
                    'ops': [
                        {
                            'op': 'add',
                            'definition': 'normal',
                            'position': [-400, 600],
                            'params': {'intensity': 5.0, 'inversedy': True},
                        }
                    ],
                    **G,
                },
            )
        )
    )
    await c('apply_edits', {'ops': [{'op': 'connect', 'from': grad, 'to': nrm, 'input': 'input1'}], **G})
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
    await c('apply_edits', {'ops': [{'op': 'set', 'node': nrm, 'params': {'inversedy': False}}], **G})
    dx = pixel_values(text(await c('node_stats', {'node_id': nrm, 'points': [[256, 256]], **G})))[(256, 256)]
    # a full-height ramp is a gentle slope (G about 0.49 vs 0.51); the sign is what matters
    check(
        F,
        'normal inversedy=True is OpenGL',
        gl[1] < 0.497 and dx[1] > 0.503 and abs(gl[1] + dx[1] - 1) < 0.002,
        'OpenGL G=%.3f, DirectX G=%.3f' % (gl[1], dx[1]),
    )
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': grad}, {'op': 'delete', 'node': nrm}], **G})
    # a Dot node (passthrough) has no ID property: Designer's UI portals store it as <userId> in the
    # file and in Designer's memory, not exposed to the API, so the API can't make one (AGENTS.md, Portals). Any id-like property here would be new
    t = text(await designer_script(c, 'facts/dot_properties'))
    props = re.search(r'DOT_PROPS=(.*)', t)
    check(
        F,
        'a Dot node has no ID property (portal IDs are not exposed to the API)',
        props is not None
        and props.group(1).split(',')
        == sorted(
            [
                '$format',
                '$outputsize',
                '$pixelratio',
                '$pixelsize',
                '$randomseed',
                '$tiling',
                'input',
                'unique_filter_output',
            ]
        ),
        t.strip()[-200:],
    )
    # a package's UID is its file's <fileUID>: unchanged by saving and Save As, shared by a copy of
    # the file loaded again; mHandle differs for every Python object wrapping one package. What
    # snapshots' package notes rely on (REVIEW.md SRV-34, SRV-36)
    uid_dir = os.path.join(scratch, 'uid_probe')
    t = text(await designer_script(c, 'facts/package_uid', folder=uid_dir))
    check(
        F,
        "a package's UID survives saving, a loaded copy and a snapshot copy share it; mHandle isn't stable",
        'SAME_UID=True' in t and 'HANDLES_DIFFER=True' in t and 'COPY_KEEPS_UID=True' in t,
        t.strip()[-150:],
    )
    # _fresh_uid's byte edit (snapshots of unsaved packages, REVIEW.md SRV-42) loads with the new UID; and
    # re-stamping a package's own file (a snapshot restored over it) leaves a package using its graph
    # working: the dependency is stored by file name, with <fileUID> "0"
    from server_tools.snapshots import _fresh_uid

    def own_uid(path: str) -> str:
        with open(path, encoding='utf-8') as f:
            return cast(re.Match[str], re.search(r'<fileUID v="([^"]+)"', f.read())).group(1)

    s_sbs, b_sbs, d_sbs = (os.path.join(uid_dir, n) for n in ('S.sbs', 'B.sbs', 'D.sbs'))
    if not all(os.path.isfile(p) for p in (s_sbs, b_sbs, d_sbs)):
        check(F, 'a re-stamped UID loads, and a package using its graph still finds it', False, t.strip()[-150:])
        return
    b_uid = own_uid(b_sbs)
    _fresh_uid(s_sbs)
    _fresh_uid(b_sbs)
    with open(d_sbs, encoding='utf-8') as f:
        dep_zero = bool(re.search(r'<dependency><filename v="B\.sbs"/>.*?<fileUID v="0"/>', f.read()))
    t = text(
        await designer_script(
            c,
            'facts/reload_uid',
            snapshot=s_sbs,
            snapshot_uid=own_uid(s_sbs),
            user=d_sbs,
            dependency=b_sbs,
            dependency_uid=own_uid(b_sbs),
        )
    )
    check(
        F,
        'a re-stamped UID loads, and a package using its graph still finds it (stored by file name)',
        own_uid(b_sbs) != b_uid and dep_zero and 'SNAP_LOADS_NEW=True' in t and 'DEP_FOUND=True' in t,
        'dependency fileUID "0": %s; %s' % (dep_zero, t.strip()[-150:]),
    )
