"""Designer facts GUIDE.md relies on (they fail if a Designer update changes them)."""

import base64
import contextlib
import os
import pathlib
import re
import shutil
import sys
from collections.abc import Sequence
from itertools import product
from textwrap import dedent
from typing import TYPE_CHECKING

import designer_helpers
from test_all_tools import common
from test_all_tools.common import (
    NO_LINE,
    TEST_GRAPH,
    Ctx,
    Ops,
    ToolArgs,
    added_id,
    check,
    designer_script,
    expect,
    is_image,
    pixel_values,
    refs,
    skip,
    text,
)
from test_all_tools.facts import state_camera, state_file
from test_all_tools.facts.blend_cases import (
    COLOURS,
    DESTINATION,
    HALF,
    MODES,
    MODES_DEPTH,
    MODES_GRAPH,
    TYPE_FEEDS,
    Feeds,
    blend_lines,
    by_mode,
    by_types,
    expected_lines,
    image,
    listed,
)
from test_all_tools.facts.preparations import STATE_GRAPH
from test_all_tools.facts.state_file import in_designer

if TYPE_CHECKING:  # for the checker: the part as the helpers hold it
    from designer_helpers import state3d
    from designer_helpers.state3d import StateField
else:
    state3d = designer_helpers.standalone('state3d')

# the state file checks write the Designer's own default 3D view state, in its own home: never the user's (off macOS,
# the self-test's Designer has no home of its own, and writes the user's AppData: REVIEW.md TST-890)
STATE_FILE_USERS = "it would write the user's default 3D view state: Designer has no home of its own here"


async def check_a_blend_opacity_fed_a_colour_image(ctx: Ctx) -> None:
    """What an atomic blend, copy, its opacitymult at its default, 1, gives with its opacity input fed each image of
    `feeds`, a row each: the opacity the blend takes from it, and the image it computes, LUM or RGBA. Its sides are
    colour, white over (0.2, 0.4, 0.6, 1), or grey, white over 0.2, each in an 8-bit, a 16-bit and a 32-bit float graph
    (facts/designer_scripts/blend_opacity.py). Then, in the float graph, each blendingmode, the enum listing MODES:
    a grey uniform 0.5 gives the blend opacitymult 0.5 gives with nothing connected, and a colour uniform (0.5, 0.5,
    0.5, 1) the one opacitymult 0 gives, the destination; those two blends differ. The cases, as GUIDE.md states
    them: A blend's opacity; Grayscale Conversion's mean: The greys of a colour image."""
    t = await blend_lines(ctx)
    feeds: Feeds = {
        'nothing': (1, ()),
        'a grey uniform 0.5': (0.5, (0.5,)),
        **{'a colour uniform %s' % listed(rgba): (0, rgba) for rgba in COLOURS},
        "a Pixel Processor's float 0.5, colorswitch on": (0, HALF),
        "a Pixel Processor's float 0.5, colorswitch off": (0.5, (0.5,)),
        'Grayscale Conversion of a colour uniform (0.2, 0.4, 0.6, 1)': (0.4, (0.4,)),
        'a bitmap of an 8-bit grey PNG at 128': (0.5, (0.5,)),
        'a bitmap of an RGB PNG at (128, 128, 128)': (0, HALF),
        # the two colour images GUIDE.md's core gives Grayscale Conversion for
        "Grayscale Conversion of a Pixel Processor's float 0.5, colorswitch on": (0.5, (0.5,)),
        'Grayscale Conversion of a bitmap of an RGB PNG at (128, 128, 128)': (0.5, (0.5,)),
    }
    expect(t, "a blend's opacity", {**expected_lines(feeds), '%s, blendingmode ids' % MODES_GRAPH: ', '.join(MODES)})
    destination = 'blend ' + image(MODES_DEPTH, *DESTINATION)
    for mode in MODES:
        got = by_mode(t, mode)
        told = 'grey %(grey)s; colour %(colour)s; opacitymult 0.5 %(half)s; opacitymult 0 %(zero)s' % got
        apart = got['half'] != got['zero']
        check(
            'designer facts',
            "a blend's opacity, %s mode: a grey uniform 0.5 gives what opacitymult 0.5 gives" % mode,
            apart and got['grey'] == got['half'],
            told,
        )
        check(
            'designer facts',
            "a blend's opacity, %s mode: a colour uniform (0.5, 0.5, 0.5, 1) gives what opacitymult 0 gives, the "
            'destination' % mode,
            apart and got['colour'] == got['zero'] == destination,
            told,
        )


async def check_a_blend_of_a_grey_image_and_a_colour_one(ctx: Ctx) -> None:
    """What an atomic blend gives when its source and destination differ in type, LUM and RGBA (ROADMAP item 127), in
    the float graph of facts/designer_scripts/blend_opacity.py: in each blendingmode of MODES, with nothing in its
    opacity and with a grey uniform 0.5 there. A grey source 0.3 over the colour destination (0.2, 0.4, 0.6, 1) gives
    what a colour source (0, 0, 0, 0) gives, the destination in every mode but switch. A colour source (0.3, 0.3, 0.3,
    1) over the grey destination 0.2 gives what a grey source 0 gives. Each differs from the blend of a source 0.3 of
    the destination's type. The case, as GUIDE.md states it: A blend of a grey image and a colour one."""
    t = await blend_lines(ctx)
    destination = 'blend ' + image(MODES_DEPTH, *DESTINATION)
    for mode, feed in product(MODES, TYPE_FEEDS):
        got = by_types(t, mode, feed)
        told = '; '.join('%s %s' % item for item in got.items())
        # every line compared is there: said() gives a note starting NO_LINE for a missing one, which differs from any
        # line (REVIEW.md TST-824)
        present = NO_LINE not in told
        name = 'a blend of a grey image and a colour one, %s mode, opacity %s: ' % (mode, feed)
        gives_destination = mode != 'switch'
        check(
            'designer facts',
            name + 'a grey source over a colour destination gives what a colour source (0, 0, 0, 0) gives, '
            '%sthe destination' % ('' if gives_destination else 'not '),
            present
            and got['grey_over_colour'] == got['clear_over_colour'] != got['colour_over_colour']
            and (got['grey_over_colour'] == destination) == gives_destination,
            told,
        )
        check(
            'designer facts',
            name + 'a colour source over a grey destination gives what a grey source 0 gives',
            present and got['colour_over_grey'] == got['black_over_grey'] != got['grey_over_grey'],
            told,
        )


async def check_curvature_smooth_takes_the_format_of_its_normals(ctx: Ctx) -> None:
    """What library curvature_smooth gives on the crest of a horizontal ridge, from atomic normal's normals of it,
    inversedy True and False, at each normal_format, DirectX 0 and OpenGL 1, as describe_node lists them. The ridge is
    a Pixel Processor's exp(-60 d²), d the distance along y to the middle of the 512 px graph. Its crest reads above
    0.5 where curvature_smooth takes it as convex, below where concave. normal_format 1 reads it convex from normals of
    inversedy True, and 0 from those of False. The other format reads it concave. The fact, as GUIDE.md states it:
    Library node facts, curvature_smooth (REVIEW.md INS-47)."""
    c, G = ctx.c, ctx.G
    F = 'designer facts'
    t = text(await c('describe_node', {'definition': 'curvature_smooth'}))
    check(
        F,
        'curvature_smooth normal_format ids: DirectX 0, OpenGL 1',
        re.search(r'^\s+normal_format\s.*\n\s+enum: DirectX=0, OpenGL=1$', t, re.M) is not None,
        '\n'.join(line for line in t.splitlines() if 'normal_format' in line or 'DirectX' in line),
    )
    curvatures = {(inversedy, fmt): 'c_%s_%d' % (inversedy, fmt) for inversedy, fmt in product((True, False), (0, 1))}
    ops: Ops = [{'op': 'add', 'definition': 'pixelprocessor', 'ref': 'ridge', 'params': {'colorswitch': False}}]
    for inversedy in (True, False):
        normal = 'n_%s' % inversedy
        ops += [
            {'op': 'add', 'definition': 'normal', 'ref': normal, 'params': {'inversedy': inversedy}},
            {'op': 'connect', 'from': 'ridge', 'to': normal, 'input': 'input1'},
        ]
        for fmt in (0, 1):
            curvature = curvatures[inversedy, fmt]
            ops += [
                {'op': 'add', 'definition': 'curvature_smooth', 'ref': curvature, 'params': {'normal_format': fmt}},
                {'op': 'connect', 'from': normal, 'to': curvature, 'input': 'input'},
            ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    try:
        await c('set_function', {'node_id': added['ridge'], 'expression': 'd = $pos.y - 0.5; exp(-d * d * 60)', **G})
        for (inversedy, fmt), curvature in curvatures.items():
            got = text(await c('node_stats', {'node_id': added[curvature], 'points': [[256, 256]], **G}))
            crest = pixel_values(got).get((256, 256))
            convex = fmt == int(inversedy)  # OpenGL 1 for the normals of inversedy True, DirectX 0 for False
            check(
                F,
                'curvature_smooth normal_format %d on normals of inversedy=%s: a horizontal ridge reads %s'
                % (fmt, inversedy, 'convex' if convex else 'concave'),
                crest is not None and (crest[0] > 0.505 if convex else crest[0] < 0.495),
                'its crest %s' % crest,
            )
    finally:
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': node} for node in added.values()], **G})


async def check_unsaved_bitmap_copies(ctx: Ctx) -> None:
    c, png = ctx.c, ctx.png
    F = 'designer facts'
    # two unsaved packages copy the same file, one after the other: GUIDE.md says the copy
    # goes to <Designer's temp folder>/Adobe/Adobe Substance 3D Designer/ with an XXXXXX- prefix, stays
    # after its package closes, and so the next copy of that name gets 1- in front
    # (REVIEW.md TST-15: the check used to test only "under the temp folder"). Designer's temp folder, not this
    # process's: launch_designer gives each Designer it starts one of its own
    t = text(await designer_script(c, 'facts/unsaved_bitmap_copies', png=png))
    copies = re.findall(r'COPY=(.*) STAYS=(\w+)', t)
    names = [os.path.basename(p) for p, _ in copies]
    folders = {os.path.normcase(os.path.realpath(os.path.dirname(p))) for p, _ in copies}
    temp = re.search(r'^TEMP=(.+)$', t, re.M)
    expected_folder = os.path.normcase(
        os.path.realpath(os.path.join(temp.group(1) if temp else '?', 'Adobe', 'Adobe Substance 3D Designer'))
    )
    check(
        F,
        "CopiedAndLinked before the first save: XXXXXX- copy in <Designer's temp folder>/Adobe/Adobe Substance 3D "
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


async def check_the_largest_output_size(ctx: Ctx) -> None:
    """An absolute $outputsize of 13 computes 8192 px, and a larger one no more: why apply_edits and sweep_param refuse
    above 13 (GUIDE.md, First sd pitfalls)."""
    c = ctx.c
    t = text(await designer_script(c, 'facts/largest_output_size'))
    check(
        'designer facts',
        '$outputsize: 13 is 8192 px, and larger values compute no more',
        all('SIZE %d 8192' % log2 in t for log2 in (13, 14, 15)),
        t,
    )


async def check_compute_takes_a_fixed_time(ctx: Ctx) -> None:
    """graph.compute() takes at least about 0.9 s whatever the graph, with nothing changed too (GUIDE.md, sd API): why
    function_states reads many cells after one compute. Measured as a floor: above 0.5 s for each compute of a 3-node
    4x4 graph, recomputed unchanged, and of a larger one."""
    c = ctx.c
    t = text(await designer_script(c, 'facts/compute_floor'))
    small = re.search(r'SMALL 4x4 ([\d.]+) ([\d.]+) ([\d.]+)', t)
    larger = re.search(r'LARGER \d+ nodes, unchanged ([\d.]+)', t)
    check(
        'designer facts',
        'graph.compute() takes over 0.5 s: a 3-node 4x4 graph, recomputed unchanged, and a larger one',
        small is not None and larger is not None and min(float(x) for x in (*small.groups(), larger.group(1))) > 0.5,
        t,
    )


async def check_function_graph_states(ctx: Ctx) -> None:
    """The table in GUIDE.md on function graphs on parameters, measured in packages of its own
    (facts/designer_scripts/function_states.py): it needs nothing of the suite."""
    c, F = ctx.c, 'designer facts'
    # the table in GUIDE.md: what a function graph on a parameter does, per state. The stored value
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


async def check_a_packages_uid_survives_saving_and_a_restamped_one_loads(ctx: Ctx) -> None:
    """A package's UID is its file's <fileUID>: unchanged by saving and Save As, shared by a copy of the file loaded
    again; mHandle differs for every Python object wrapping one package. What snapshots' package notes rely on
    (REVIEW.md SRV-34, SRV-36). And _fresh_uid's byte edit loads with the new UID (REVIEW.md SRV-42)."""
    c, scratch = ctx.c, ctx.scratch
    F = 'designer facts'
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

    def own_uid(path: str) -> str | None:
        return _file_uid(pathlib.Path(path).read_text(encoding='utf-8'))

    s_sbs, b_sbs, d_sbs = (os.path.join(uid_dir, n) for n in ('S.sbs', 'B.sbs', 'D.sbs'))
    # a package saved with no fileUID fails the check, and the category goes on (REVIEW.md TST-945)
    if not all(os.path.isfile(p) for p in (s_sbs, b_sbs, d_sbs)) or None in (own_uid(s_sbs), own_uid(b_sbs)):
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


def _file_uid(package: str) -> str | None:
    """The UID in a package's file text `package`, its first <fileUID>; None when it holds none."""
    found = re.search(r'<fileUID v="([^"]+)"', package)
    return found.group(1) if found else None


def skipped_in_users(ctx: Ctx, *names: str, shots: Sequence[str] = ()) -> bool:
    """Whether the run's Designer has no home of its own, the checks then skipped: `names` as designer facts, `shots`
    as screenshot_designer's, each under the tool it is checked under (REVIEW.md TST-959). Such a Designer is the user's,
    or one started off macOS. The state file checks write the Designer's own default 3D view state."""
    users = ctx.was_running or sys.platform != 'darwin'
    if users:
        for name in names:
            skip('designer facts', name, STATE_FILE_USERS)
        for name in shots:
            skip('screenshot_designer', name, STATE_FILE_USERS)
    return users


async def check_the_3d_views_state_file_is_saved_and_loaded_in_designers_own_home_showing_nothing(ctx: Ctx) -> None:
    """Save Current State As Default and Reset Scene, where the file is and what they show (state_file.py)."""
    F = 'designer facts'
    what = "Save Current State As Default and Reset Scene: the state file in Designer's own home, nothing shown"
    if skipped_in_users(ctx, what):
        return
    from server_tools.core import _designer_data_dir

    async with state_file.kept(ctx) as kept:
        t = await in_designer(ctx, state_file.ENTRIES)
        saved = state3d._state_text(kept.path) if os.path.isfile(kept.path) else ''
    home, version = state_file.printed(t, 'HOME') or '', state_file.printed(t, 'VERSION') or ''
    where = os.path.join(_designer_data_dir(home), '.'.join(version.split('.')[:2]), state_file.NAME)
    format_version = state_file.fields(saved).get('/settingsInfo/version') if saved else None
    untrue = [key for key in state_file.ENTRIES_SAID if state_file.printed(t, key) != 'True']
    check(
        F,
        what,
        # common.PORT, read now: alone.run(port=...) sets it after this module is imported
        home == os.path.join(common.agent_folder(common.PORT), 'home')
        and state_file.printed(t, 'PATH') == where
        and format_version == state3d.STATE_VERSION
        and not untrue,
        'not so: %s; format version %s; %s' % (untrue, format_version, ' '.join(t.split())[-200:]),
    )


async def check_a_3d_shots_set_up_is_designers_state_as_it_renders(ctx: Ctx) -> None:
    """A shot's mesh, tiling and light, through the state file, are what Designer holds as it renders, as a Save then
    writes them and state3d.py reads them: the tiling written with no *, the background's map the environment's
    (designer_helpers/scene3d.py). The user's camera is put away from Frame's framing first: the shot's new mesh is
    framed as the Scene menu frames it, the user's camera's direction kept (check_the_scene_menus_mesh_switch_...)."""
    what = "screenshot_designer('3d')'s mesh, tiling and light are Designer's state as it renders"
    framed = "screenshot_designer('3d', mesh=...) frames the new mesh from the user's camera's direction"
    if skipped_in_users(ctx, shots=[what, framed]):
        return
    async with state_file.kept(ctx) as kept:
        at = state_camera.pose(kept.base)
        users = state3d.Pose(state_camera.UNFRAMED, 60.0, 15.0, at.distance * 1.4)
        state3d._state_write(kept.path, state3d._state_edited(kept.base, {'camera': users}))
        t = await in_designer(ctx, state_file.DOCKED_THEN_LOADED)
        viewport = state_file.pair(t, 'VIEWPORT')
        copy = os.path.join(ctx.scratch, 'state_saved_as_a_shot_renders.sbsscn')
        shot = os.path.join(ctx.scratch, 'state_shot.png')
        t = await in_designer(ctx, state_file.SET_UP_THEN_SAVED % (copy, shot))
        saved = state3d._state_text(copy) if os.path.isfile(copy) else ''
    if not saved:
        check('screenshot_designer', what, False, 'nothing saved as the shot rendered: %s' % ' '.join(t.split())[-200:])
        check('screenshot_designer', framed, False, 'nothing saved as the shot rendered')
        return
    values = state3d._state_fields(saved, ['mesh', 'tiling', 'environment', 'rotation', 'exposure'])
    held = state_file.fields(saved)
    tiling = held.get('/database/materials/materials/_1/material/parameters/___usd___tiling')
    background = held.get('/database/scene_textures/panorama')
    check(
        'screenshot_designer',
        what,
        values
        == {'mesh': 'sphere', 'tiling': 2.5, 'environment': state_file.AIRPORT, 'rotation': 0.25, 'exposure': 1.5}
        and tiling == 'float(2.5)'
        and background == '[(loaderType)(file)][(file)(%s)]' % state_file.AIRPORT,
        '%s; the tiling written %s, the background %s' % (values, tiling, background),
    )
    rendered = state_camera.pose(saved)
    check(
        'screenshot_designer',
        framed,
        state_camera.alike(rendered, state3d._reframed(users, 'sphere', viewport)),
        'the user at %s; as it rendered %s' % (state_camera.said(users), state_camera.said(rendered)),
    )


async def check_the_state_files_rotation_is_in_turns_and_its_intensity_the_exposure(ctx: Ctx) -> None:
    """A state file with the tiling 2.3, the environment's rotation 0.3 and its intensity 0.7, loaded: Designer's own
    Environment > Edit properties shows 108 degrees and an Exposure of 0.7, the units the set-up writes them in. A Save
    then holds each as the 32-bit float Designer holds, to 9 significant digits, so the set-up compares them so
    (state3d.py, _float32)."""
    units = "the state file's environment rotation is in turns and its intensity the Exposure, as Designer shows them"
    held = "Designer holds the state file's tiling, rotation and exposure as 32-bit floats, and saves them so"
    if skipped_in_users(ctx, units, held):
        return
    async with state_file.kept(ctx) as kept:
        edited = state3d._state_edited(kept.base, {'tiling': 2.3, 'rotation': 0.3, 'exposure': 0.7})
        state3d._state_write(kept.path, edited)
        t = await in_designer(ctx, state_file.LOADED_THEN_SAVED + '\n_sf_environment_shown()')
        saved = state3d._state_text(kept.path)
    shown = [float(state_file.printed(t, key) or 'nan') for key in ('DEGREES', 'EXPOSURE')]
    check(
        'designer facts',
        units,
        abs(shown[0] - 108) < 1e-3 and abs(shown[1] - 0.7) < 1e-6 and state_file.printed(t, 'LOADED') == 'True',
        'degrees %s, exposure %s | %s' % (*shown, ' '.join(t.split())[-150:]),
    )
    # each number's text as saved, where state3d.py finds it
    numbers = [state3d._located(saved, field)[0].group(2) for field in ('tiling', 'rotation', 'exposure')]
    check('designer facts', held, numbers == ['2.29999995', '0.300000012', '0.699999988'], 'saved: %s' % numbers)


async def check_a_dropped_maps_url_is_the_one_the_set_up_writes(ctx: Ctx) -> None:
    """Designer's maps dropped on the 3D view, as from its Library: a Save holds each as the URL
    view3d._environment_maps gives it, `sd-3dview-maps://` and the file's name, a space and a capital kept. A graph's
    outputs on the mesh, the folder beside the state file holds their textures, and no map (state3d.py; all 34
    measured, 2026-11-26)."""
    what = "a map dropped on the 3D view is saved as the URL the set-up writes, and isn't copied beside the state file"
    if skipped_in_users(ctx, what):
        return
    c = ctx.c
    async with state_file.kept(ctx):
        await c('open_graph', ctx.G)  # another graph, then STATE_GRAPH: its outputs on the mesh
        await c('open_graph', {'graph': STATE_GRAPH})
        t = await in_designer(ctx, state_file.DROPPED % ['studio 02', 'Soft_1Front'])
        await c('open_graph', ctx.G)  # the editor back on the category's graph
    dropped = [line.split('=', 1)[1].split('|') for line in t.splitlines() if line.startswith('DROPPED=')]
    check(
        'designer facts',
        what,
        len(dropped) == 2
        and all(
            saved == written and 'default_baseColor.png' in files and not re.search(r'\.(exr|hdr)', files)
            for _, saved, written, files in dropped
        ),
        '; '.join(' '.join(d) for d in dropped) or ' '.join(t.split())[-200:],
    )


async def check_the_scene_menus_mesh_switch_frames_the_mesh_from_the_cameras_direction(ctx: Ctx) -> None:
    """Each mesh picked in the Scene menu, with no Frame, from a camera put at another direction, away from any mesh's
    framing: the file holds the mesh by the table's id, and the camera keeps its direction and looks at the new mesh's
    point from its distance at the viewport's aspect (state3d._framing), docked and floated wider than tall. mesh=
    frames the new mesh so, through the state file (designer_helpers/scene3d.py)."""
    switched = "the Scene menu's mesh switch frames the mesh from the camera's direction, in a viewport %s"
    sizes = {'docked': None, 'wider than tall': (700, 420)}
    if skipped_in_users(ctx, *(switched % size for size in sizes)):
        return
    async with state_file.kept(ctx) as kept:
        # each a mesh the view doesn't show as it is picked: one shown already, picked again, changes nothing
        docked = ['Plane', 'Torus', 'Cylinder', 'Mat ball', 'Sphere', 'Cloth']
        if state3d.FRAMING[docked[0]][0] == state3d._state_fields(kept.base, ['mesh'])['mesh']:
            docked = docked[1:] + docked[:1]
        wider = ['Torus', 'Plane'] if docked[-1] == 'Plane' else ['Plane', 'Torus']
        meshes = {'docked': docked, 'wider than tall': wider}
        at = state_camera.pose(kept.base)
        away = state3d.Pose(state_camera.UNFRAMED, 30.0, 20.0, at.distance * 1.4)
        state3d._state_write(kept.path, state3d._state_edited(kept.base, {'camera': away}))
        await in_designer(ctx, '_sf_load()')
        switches = [
            (
                size,
                [
                    (mesh, os.path.join(ctx.scratch, 'state_switched_%d_%d.sbsscn' % (i, j)))
                    for j, mesh in enumerate(meshes[name])
                ],
            )
            for i, (name, size) in enumerate(sizes.items())
        ]
        t = await in_designer(ctx, state_file.SWITCHED % switches)
        seen = [state_file.pair(line, 'VIEWPORT') for line in t.splitlines() if line.startswith('VIEWPORT=')]
    for i, (name, (_, pairs)) in enumerate(zip(sizes, switches, strict=True)):
        if len(seen) <= i:
            check('designer facts', switched % name, False, 'no viewport said: %s' % ' '.join(t.split())[-200:])
            continue
        off = []
        for mesh, path in pairs:
            got = state3d._state_fields(state3d._state_text(path), ['mesh', 'camera']) if os.path.isfile(path) else None
            mesh_id = state3d.FRAMING[mesh][0]  # the mesh's id in the file, which the table holds
            want = state3d._reframed(away, mesh_id, seen[i])
            if got is None or got['mesh'] != mesh_id or not state_camera.alike(got['camera'], want):
                held = got and '%s %s' % (got['mesh'], state_camera.said(got['camera']))
                off.append('%s %s, framed %s' % (mesh, held, state_camera.said(want)))
        check(
            'designer facts',
            switched % name,
            not off,
            'viewport %dx%d; %s' % (*seen[i], '; '.join(off) or 'each mesh framed so'),
        )


async def check_a_state_file_with_another_mesh_loads_it_keeping_the_files_camera(ctx: Ctx) -> None:
    """A state file with another mesh's id and a camera away from that mesh's framing, loaded: Designer shows the mesh
    and keeps the file's camera, framing nothing, so the set-up writes the camera framed with the mesh (state3d.py)."""
    what = "a state file with another mesh loads it with the file's camera: Designer doesn't frame the new mesh"
    if skipped_in_users(ctx, what):
        return
    async with state_file.kept(ctx) as kept:
        held = state3d._state_fields(kept.base, ['mesh', 'camera'])
        other = 'plane' if held['mesh'] != 'plane' else 'sphere'
        written = state3d.Pose(state_camera.UNFRAMED, 60.0, 15.0, held['camera'].distance * 1.3)
        state3d._state_write(kept.path, state3d._state_edited(kept.base, {'mesh': other, 'camera': written}))
        t = await in_designer(ctx, '_sf_sized(None)\n' + state_file.LOADED_THEN_SAVED)
        after = state3d._state_fields(state3d._state_text(kept.path), ['mesh', 'camera'])
    framed = state3d._reframed(written, other, state_file.pair(t, 'VIEWPORT'))
    check(
        'designer facts',
        what,
        after['mesh'] == other
        and state_camera.alike(after['camera'], written)
        and not state_camera.alike(after['camera'], framed)
        and state_file.printed(t, 'LOADED') == 'True',
        'mesh %s, camera %s; written %s, framed %s'
        % (after['mesh'], state_camera.said(after['camera']), state_camera.said(written), state_camera.said(framed)),
    )


async def check_a_load_of_a_mesh_of_the_users_own_ends_once_the_view_settled(ctx: Ctx) -> None:
    """A state file holding a mesh of the user's own, Designer's own box.fbx by its file:// URL, loaded: the Scene menu
    checks no mesh as Reset Scene returns, nor once the view settled after it. The load restarts the view within
    SETTLE_LIMIT, and the state saved once the view settled holds the mesh, so the load had ended by then
    (designer_helpers/scene3d.py, _state_load; REVIEW.md HLP-283, HLP-286). A 3D shot with a camera option over it says
    nothing of a view that hadn't settled."""
    fact = (
        "a mesh of the user's own: the Scene menu checks no mesh, the load restarts the view, and it has ended once"
        ' the view settled'
    )
    shot = "screenshot_designer('3d') over a mesh of the user's own takes each load as ended once the view settled"
    if skipped_in_users(ctx, fact, shots=[shot]):
        return
    box = state_file.printed(await in_designer(ctx, state_file.BOX_PATH), 'BOX')
    if not box:
        check('designer facts', fact, False, "Designer's resources hold no python/tests/assets/box.fbx")
        check('screenshot_designer', shot, False, 'no mesh of the users own to load')
        return
    url = state3d.USERS_MESH + box
    async with state_file.kept(ctx) as kept:
        state3d._state_write(kept.path, state3d._state_edited(kept.base, {'mesh': url}))
        t = await in_designer(ctx, state_file.LOADED_SETTLED)
        saved = state3d._state_fields(state3d._state_text(kept.path), ['mesh'])['mesh']
        r = await ctx.c('screenshot_designer', ORBIT)
    expected = {'AT_TRIGGER': '[]', 'RESTARTED': 'True', 'SETTLED': 'True', 'AFTER': '[]'}
    said = {key: state_file.printed(t, key) for key in expected}
    check(
        'designer facts',
        fact,
        said == expected and saved == url,
        'read %s, expected %s; the state saved holds %s' % (said, expected, saved),
    )
    check(
        'screenshot_designer',
        shot,
        is_image(r) and "hadn't settled" not in text(r) and '3D view: put back as it was' in text(r),
        ' / '.join(line for line in text(r).splitlines() if line.startswith('3D view'))[-250:],
    )


async def check_a_state_file_with_one_field_edited_loads_that_field_alone(ctx: Ctx) -> None:
    """Each field the set-up edits, edited alone (state_file.ONE_FIELD), loads: the state saved after the load is the
    one written, but the fields that follow it. A Save once the load has ended holds the camera the camera's row turns
    still on its way, and the others' where it was; one once the view's count has risen holds the file's camera
    (state_file.py; REVIEW.md TST-892)."""
    F = 'designer facts'
    loads = 'a state file with only its %s edited loads it'
    if skipped_in_users(ctx, *(loads % row.name for row in state_file.ONE_FIELD)):
        return
    async with state_file.kept(ctx) as kept:
        # the state once drawn, its camera put at AWAY: a view that hasn't drawn yet saves fields it sets as it draws (a
        # material's blue noise, the rasterizer's settings), which a load drawn on screen would show as changed
        state3d._state_write(kept.path, state_camera.away(kept.base))
        await in_designer(ctx, state_file.LOADED_THEN_SAVED)
        base = state3d._state_text(kept.path)
        session = state_camera.pose(base)  # the camera the session has, which each load moves
        mid = os.path.join(ctx.scratch, 'state_saved_at_the_loads_end.sbsscn')
        for row in state_file.ONE_FIELD:
            written = row.edit(base)
            state3d._state_write(kept.path, written)
            t = await in_designer(ctx, state_file.MID_LOADED_THEN_SAVED % mid)
            after = state3d._state_text(kept.path)
            changed = state_file.differing(base, written)
            left = state_file.not_loaded(changed, written, after, row.follows)
            wanted = state_camera.pose(written)
            # at the load's end, a camera turned is still on its way; one the session had is where it was
            turning = state_camera.turned_apart(session, wanted) > 0.01
            session = state_camera.pose(after)
            if state_file.printed(t, 'MID_SAVED') != 'True':  # REVIEW.md TST-911: no Save at the load's end, said
                check(F, loads % row.name, False, "no Save at the load's end: " + ' '.join(t.split())[-120:])
                continue
            apart = state_camera.turned_apart(wanted, state_camera.pose(state3d._state_text(mid)))
            check(
                F,
                loads % row.name,
                bool(changed)
                and not left
                and (apart > 1 if turning else apart < 0.01)
                and state_file.printed(t, 'LOADED') == 'True',
                "differing after the load %s; the camera at the load's end %.2f degrees off the file's; edited %s"
                % (left[:4], apart, changed[:3]),
            )


async def check_a_state_file_missing_its_lights_loads_them_at_designers_defaults(ctx: Ctx) -> None:
    """A file with the camera alone of the scene's entities, after one turning Point Light 1 on loaded, brings the
    light back off (state_file.py, the format)."""
    F = 'designer facts'
    what = "a state file missing its lights loads them at Designer's defaults"
    if skipped_in_users(ctx, what):
        return
    async with state_file.kept(ctx) as kept:
        lit = state_file.edited(kept.base, state_file.LIGHT_ON, r'\1true\2')
        state3d._state_write(kept.path, lit)
        t = await in_designer(ctx, state_file.LOADED_THEN_SAVED)
        on = state_file.entity(state3d._state_text(kept.path), 'Point Light 1')
        state3d._state_write(kept.path, state_file.edited(lit, state_file.LIGHTS, state_file.CAMERA_ONLY))
        t += await in_designer(ctx, state_file.LOADED_THEN_SAVED)
        off = state_file.entity(state3d._state_text(kept.path), 'Point Light 1')
    check(
        F,
        what,
        on.get('/is_enabled') == 'true' and off.get('/is_enabled') == 'false' and 'LOADED=False' not in t,
        'Point Light 1 on: %s, after the file without it: %s' % (on.get('/is_enabled'), off.get('/is_enabled')),
    )


async def check_reset_scene_reads_the_state_file_once_it_has_returned(ctx: Ctx) -> None:
    """A file written right after Reset Scene's trigger, in the same job, is the one loaded (state_file.py)."""
    F = 'designer facts'
    what = 'Reset Scene reads the state file once it has returned'
    if skipped_in_users(ctx, what):
        return
    async with state_file.kept(ctx) as kept:
        later = os.path.join(ctx.scratch, 'state_written_after_the_trigger.sbsscn')
        state3d._state_write(later, state3d._state_edited(kept.base, {'rotation': 0.375}))
        state3d._state_write(kept.path, state3d._state_edited(kept.base, {'rotation': 0.125}))
        t = await in_designer(ctx, state_file.WRITTEN_AFTER_THE_TRIGGER % later)
        rotation = state3d._state_fields(state3d._state_text(kept.path), ['rotation']).get('rotation')
    check(F, what, rotation == 0.375 and 'LOADED=True' in t, 'rotation loaded %s' % rotation)


async def check_designers_frame_gives_the_view_tables_poses(ctx: Ctx) -> None:
    """Designer's own Camera > <view>, then Frame, against the pose `view=` writes (state3d._framed): each view on the
    Plane, in the self-test's 3D panel as it is, looks along its direction at the table's point and distance. Then each
    mesh of the Scene menu, framed by Frame in the 3D panel floated to a size taller than wide, then to one wider than
    tall: the file holds it by the table's id, and the camera looks at the table's point from its distance at the
    viewport's aspect (state3d.FRAMING, FRAME_ANGLE; the user's design, 2026-11-25). The camera's decode is state3d's
    (state_camera.pose)."""
    F = 'designer facts'
    what_views = "the state file camera: each view framed on the Plane is view='s pose"
    framed = "the state file camera: each mesh framed in a viewport of %s is the view table's pose"
    sizes = {'a panel taller than wide': (300, 500), 'a panel wider than tall': (700, 420)}
    if skipped_in_users(ctx, what_views, *(framed % size for size in sizes)):
        return
    async with state_file.kept(ctx):
        paths = {view: os.path.join(ctx.scratch, 'state_view_%s.sbsscn' % view) for view in state3d.VIEW_DIRECTIONS}
        t = await in_designer(ctx, '_sf_sized(None)\n' + state_file.VIEWED % list(paths.items()))
        viewport = state_file.pair(t, 'VIEWPORT')
        poses = {view: state_camera.pose(state3d._state_text(path)) for view, path in paths.items()}
        wanted = {view: state3d._framed('plane', view, viewport) for view in poses}
        check(
            F,
            what_views,
            all(state_camera.alike(at, wanted[view]) for view, at in poses.items()),
            '; '.join(
                '%s %s, the table %s' % (v, state_camera.said(p), state_camera.said(wanted[v]))
                for v, p in poses.items()
            ),
        )
        framings = [
            (
                size,
                [
                    (mesh, os.path.join(ctx.scratch, 'state_framed_%d_%d.sbsscn' % (i, j)))
                    for j, mesh in enumerate(state3d.FRAMING)
                ],
            )
            for i, size in enumerate(sizes.values())
        ]
        t = await in_designer(ctx, state_file.FRAMED % framings)
        # the viewport of each size, then docked again
        seen = [state_file.pair(line, 'VIEWPORT') for line in t.splitlines() if line.startswith('VIEWPORT=')]
    for i, (name, (_, meshes)) in enumerate(zip(sizes, framings, strict=True)):
        if len(seen) <= i:
            check(F, framed % name, False, 'no viewport said: %s' % ' '.join(t.split())[-200:])
            continue
        width, height = seen[i]
        off = []
        for mesh, path in meshes:
            got = state3d._state_fields(state3d._state_text(path), ['mesh', 'camera']) if os.path.isfile(path) else None
            mesh_id = state3d.FRAMING[mesh][0]  # the mesh's id in the file, which the table holds (REVIEW.md TST-933)
            want = state3d._framed(mesh_id, 'Front', seen[i])
            # Frame keeps the camera's direction: its point and distance compared
            if (
                got is None
                or got['mesh'] != mesh_id
                or not state_camera.alike(got['camera']._replace(yaw=0.0, pitch=0.0), want)
            ):
                held = got and '%s %s' % (got['mesh'], state_camera.said(got['camera']))
                off.append('%s %s, the table %s' % (mesh, held, state_camera.said(want)))
        check(
            F,
            framed % name,
            (width < height) == (name == 'a panel taller than wide') and not off,
            'viewport %dx%d; %s' % (width, height, '; '.join(off) or 'each mesh as the table'),
        )


async def check_after_a_load_the_3d_view_follows_the_graph_once_another_graph_and_it_are_opened(ctx: Ctx) -> None:
    """A graph opened puts its outputs on the mesh, Save writing their textures. A load leaves them; a Save after it
    writes none and deletes their folder, until another graph, then that one, are opened (state_file.py; REVIEW.md
    TST-901, TST-909)."""
    F = 'designer facts'
    what = 'after a load the 3D view follows the graph again once another graph, then it, are opened'
    if skipped_in_users(ctx, what):
        return
    c = ctx.c
    async with state_file.kept(ctx) as kept:
        folder = state3d._state_resources(kept.path)

        def listed() -> list[str] | None:  # the folder's textures; None: no folder
            return sorted(os.listdir(folder)) if os.path.isdir(folder) else None

        async def textures_saved() -> list[str] | None:
            await in_designer(ctx, state_file.COMPUTED_THEN_SAVED % STATE_GRAPH)
            return listed()

        await c('open_graph', {'graph': STATE_GRAPH})
        linked = await textures_saved()
        await in_designer(ctx, '_sf_load()')
        left_by_the_load = listed()  # REVIEW.md TST-909: the Save, not the load, deletes the folder
        loaded = await textures_saved()
        await c('open_graph', ctx.G)  # another graph, then STATE_GRAPH again
        await c('open_graph', {'graph': STATE_GRAPH})
        relinked = await textures_saved()
        await c('open_graph', ctx.G)  # the editor back on the category's graph
    textures = ['default_baseColor.png', 'default_roughness.png']
    check(
        F,
        what,
        linked == left_by_the_load == relinked == textures and loaded is None,
        'textures saved: linked %s; after a load %s, then saved %s; relinked %s'
        % (linked, left_by_the_load, loaded, relinked),
    )


async def check_a_state_file_load_resets_the_aov_and_keeps_the_renderer_and_displacement(ctx: Ctx) -> None:
    """The AOV set to Material roughness, then a load. Then, the file saved with the Rasterizer and the Displacement
    toggle as they were, the GPU Pathtracer set and the toggle flipped, then a load: both stay as the session has them
    (state_file.py; REVIEW.md TST-893, TST-904)."""
    F = 'designer facts'
    what_aov = "a state file's load puts the 3D view's AOV back to Beauty"
    what_renderer = "a state file's load keeps the session's renderer and Displacement toggle, the GPU Pathtracer set"
    if skipped_in_users(ctx, what_aov, what_renderer):
        return
    async with state_file.kept(ctx):
        t = await in_designer(ctx, state_file.VIEW_SETTINGS)
    said = {key: state_file.printed(t, key) for key in state_file.VIEW_SETTINGS_SAID}
    detail = ', '.join('%s %s' % (key.lower(), value) for key, value in said.items())
    check(F, what_aov, (said['AOV_SET'], said['AOV_LOADED']) == ("['Material roughness']", "['Beauty']"), detail)
    check(
        F,
        what_renderer,
        said['RENDERER_SAVED'] == "['Rasterizer']"
        and said['RENDERER_SET'] == said['RENDERER_LOADED'] == "['GPU Pathtracer']"
        and said['DISPLACEMENT_SET'] == said['DISPLACEMENT_LOADED'] != said['DISPLACEMENT_SAVED']
        and said['PUT_BACK'] == 'True',
        detail,
    )


async def check_a_state_file_load_turns_override_material_on_though_the_file_holds_it_off(ctx: Ctx) -> None:
    """Materials > Override Material turned off, a graph's outputs on the mesh, then the state saved and loaded: the
    file holds it off, and the load turns it on (state_file.py; REVIEW.md HLP-267: the set-up sets it back after each
    load, designer_helpers/scene3d.py)."""
    what = "a state file's load turns Materials > Override Material on, though the file holds it off"
    if skipped_in_users(ctx, what):
        return
    c = ctx.c
    async with state_file.kept(ctx):  # its end loads the base again, which turns it on
        await c('open_graph', ctx.G)  # another graph, then STATE_GRAPH: its outputs on the mesh, and the entry there
        await c('open_graph', {'graph': STATE_GRAPH})
        t = await in_designer(ctx, state_file.OVERRIDE_LOADED)
        await c('open_graph', ctx.G)  # the editor back on the category's graph
    said = {key: state_file.printed(t, key) for key in ('OFF', 'SAVED_OFF', 'OVERRIDDEN')}
    check(
        'designer facts',
        what,
        said == {'OFF': 'False', 'SAVED_OFF': 'True', 'OVERRIDDEN': 'True'},
        'turned off: checked %s; the file holds it off %s; loaded: checked %s | %s'
        % (said['OFF'], said['SAVED_OFF'], said['OVERRIDDEN'], t.strip()[-200:]),
    )


# a 3D shot with every set-up option the state file and the menus set, through the tool
EVERY_SET_UP: ToolArgs = {
    'panel': '3d',
    'max_size': 256,
    'graph': STATE_GRAPH,
    'mesh': 'Sphere',
    'view': 'Top',
    'orbit': [30, 10],
    'pan': [0.1, 0.05],
    'zoom': 2,
    'tiling': 2.0,
    'environment': 'airport',
    'environment_rotation': 90,
    'environment_exposure': 1.0,
}
ORBIT: ToolArgs = {'panel': '3d', 'max_size': 256, 'orbit': [30, 0]}  # a shot with a camera option alone


def kept_files(path: str) -> dict[str, bytes]:
    """The state file `path` and the textures' folder beside it, each file by its path, as bytes."""
    folder = state3d._state_resources(path)
    files = [path] if os.path.isfile(path) else []
    files += [os.path.join(folder, name) for name in sorted(os.listdir(folder))] if os.path.isdir(folder) else []
    return {file: pathlib.Path(file).read_bytes() for file in files}


def users_files(path: str) -> None:
    """A default state file and textures' folder of the user's own at `path`: bytes no Save writes."""
    with open(path, 'wb') as f:
        f.write(b'<the users own default, not even a state file/>\r\n')
    os.makedirs(state3d._state_resources(path), exist_ok=True)
    with open(os.path.join(state3d._state_resources(path), 'theirs.png'), 'wb') as f:
        f.write(b'their texture')


async def check_a_3d_shot_puts_the_users_3d_view_and_default_state_file_back(ctx: Ctx) -> None:
    """A shot with every set-up option: the user's default state file and textures' folder, of bytes no Save writes,
    are back byte for byte after it, the shot's backup gone; and the state saved then holds the same camera, mesh,
    environment and tiling as the one saved before it (designer_helpers/scene3d.py; the user's design, ROADMAP item
    131). The shot says what it set, then that the view was put back. With neither file nor folder, a shot leaves
    neither, and it leaves Override Material off when the user had it off, which a load turns on (REVIEW.md
    HLP-267). The user's AOV, Material roughness, is shown again after it, which a load puts back to Beauty (REVIEW.md
    TST-941)."""
    view = "screenshot_designer('3d') with a set-up puts the user's 3D view back: camera, mesh, environment and tiling"
    what = "screenshot_designer('3d') with a set-up puts the default state file and its folder back byte for byte"
    none = "screenshot_designer('3d') with a set-up leaves no default state file where there was none"
    overridden = "screenshot_designer('3d') with a set-up leaves Materials > Override Material off, as the user had it"
    aov_back = "screenshot_designer('3d') with a set-up shows the user's AOV again, which a load puts back to Beauty"
    if skipped_in_users(ctx, shots=[view, what, none, overridden, aov_back]):
        return
    async with state_file.kept(ctx) as kept:
        users_files(kept.path)
        before = kept_files(kept.path)
        picked = state_file.printed(await in_designer(ctx, state_file.AOV_SHOWN % 'Material roughness'), 'AOV')
        try:
            r = await ctx.c('screenshot_designer', EVERY_SET_UP)
        finally:  # the AOV after the shot, then Beauty again
            aov = state_file.printed(await in_designer(ctx, state_file.AOV_READ_BACK), 'AOV')
        check(
            'screenshot_designer',
            aov_back,
            is_image(r) and picked == aov == "['Material roughness']",
            'picked %s; after the shot %s' % (picked, aov),
        )
        after = kept_files(kept.path)
        check(
            'screenshot_designer',
            what,
            is_image(r) and after == before and not os.path.exists(state_file.backup(kept.path)),
            'files before %s, after %s | %s' % (sorted(before), sorted(after), text(r).strip()[-200:]),
        )
        # saved, then the user's Override Material off, which a load turns on (REVIEW.md HLP-267); kept's end loads it
        # on again
        turned_off = state_file.printed(
            await in_designer(ctx, "_sf_save(); print('OFF=%s' % _sf_override(False))"), 'OFF'
        )
        saved = state3d._state_text(kept.path)
        with contextlib.suppress(FileNotFoundError):
            os.remove(kept.path)
        shutil.rmtree(state3d._state_resources(kept.path), ignore_errors=True)
        orbit = await ctx.c('screenshot_designer', ORBIT)
        left = kept_files(kept.path)
        override = state_file.printed(await in_designer(ctx, "print('OVERRIDE=%s' % _sf_override())"), 'OVERRIDE')
        check(
            'screenshot_designer',
            overridden,
            is_image(orbit) and (turned_off, override) == ('False', 'False'),
            'checked when turned off %s, after the shot %s | %s' % (turned_off, override, text(orbit).strip()[-200:]),
        )
        check(
            'screenshot_designer',
            none,
            is_image(orbit) and not left,
            'left %s | %s' % (sorted(left), text(orbit)[-200:]),
        )
    names: list[StateField] = ['mesh', 'tiling', 'environment', 'rotation', 'exposure']
    before_fields, after_fields = state3d._state_fields(kept.base, names), state3d._state_fields(saved, names)
    camera = [state_camera.pose(content) for content in (kept.base, saved)]
    said = [line for line in text(r).splitlines() if line.startswith('3D view: ')]
    check(
        'screenshot_designer',
        view,
        is_image(r)
        and before_fields == after_fields
        and state_camera.alike(*camera)
        and said[-1:] == ['3D view: put back as it was']
        and any('Sphere' in line and 'view Top' in line for line in said),
        'before %s, %s; after %s, %s | %s'
        % (before_fields, state_camera.said(camera[0]), after_fields, state_camera.said(camera[1]), ' / '.join(said)),
    )


async def check_a_3d_shot_puts_a_leftover_backup_back_first(ctx: Ctx) -> None:
    """A backup an earlier call left, as a crash between its backup and its put-back would, is put back before the
    shot's own, and said: the user's file comes back, not ours (scene3d.py, state3d._state_back_up)."""
    what = "screenshot_designer('3d') puts a backup an earlier call left back first, and says so"
    if skipped_in_users(ctx, shots=[what]):
        return
    async with state_file.kept(ctx) as kept:
        users_files(kept.path)
        before = kept_files(kept.path)
        state3d._state_back_up(kept.path, state_file.backup(kept.path))
        state3d._state_write(kept.path, '<ours, left by a call that never ended/>')
        r = await ctx.c('screenshot_designer', ORBIT)
        after = kept_files(kept.path)
    check(
        'screenshot_designer',
        what,
        is_image(r) and after == before and '3D view: ' + state3d.LEFTOVER_PUT_BACK % kept.path in text(r),
        'the files back: %s | %s' % (after == before, text(r).strip()[-300:]),
    )


async def check_a_3d_shot_removes_a_leftover_backup_it_cant_put_back_and_says_so(ctx: Ctx) -> None:
    """A backup an earlier call left that records no path (one made before REVIEW.md HLP-257's fix) is removed, said,
    and the shot goes on, putting the user's file back (the user, 2026-11-26)."""
    what = "screenshot_designer('3d') removes a backup it can't put back, says so, and goes on"
    if skipped_in_users(ctx, shots=[what]):
        return
    async with state_file.kept(ctx) as kept:
        users_files(kept.path)
        before = kept_files(kept.path)
        os.makedirs(os.path.join(state_file.backup(kept.path), 'folder'))  # a backup, recording no path
        r = await ctx.c('screenshot_designer', ORBIT)
        after = kept_files(kept.path)
        gone = not os.path.exists(state_file.backup(kept.path))
    said = '3D view: ' + state3d.LEFTOVER_REMOVED % 'it records no path'
    check(
        'screenshot_designer',
        what,
        is_image(r) and gone and after == before and said in text(r),
        'removed %s, the files back %s | %s' % (gone, after == before, text(r).strip()[-300:]),
    )


# shoot_3d with the base saved without its camera, as a file of another layout would be: refused before anything changes
CAMERA_LEFT_OUT = dedent("""
    _sf_real_save = _state_save
    def _state_save(bar, keep):
        _sf_real_save(bar, keep)
        _state_write(_sf_path(), _state_text(_sf_path()).replace('<name>Default Camera</name>', '<name>Other</name>'))
    shoot_3d(%r, None, None, None, 0, None, (30.0, 0.0))""")


async def check_a_3d_shot_refuses_a_state_file_missing_a_field_and_writes_nothing(ctx: Ctx) -> None:
    """A base saved without the field a call edits (the camera) is refused before anything changes: no render, the
    user's files back byte for byte, and the session's camera as it was (scene3d.py)."""
    what = "screenshot_designer('3d') refuses a state file missing a field it edits, and writes nothing"
    if skipped_in_users(ctx, shots=[what]):
        return
    async with state_file.kept(ctx) as kept:
        users_files(kept.path)
        before = kept_files(kept.path)
        shot = os.path.join(ctx.scratch, 'state_refused.png')
        t = await in_designer(ctx, CAMERA_LEFT_OUT % shot)
        after = kept_files(kept.path)
        await in_designer(ctx, '_sf_save()')
        camera = [state_camera.pose(content) for content in (kept.base, state3d._state_text(kept.path))]
    refused = "holds the camera's <local_transform> 0 times" in t and not os.path.exists(shot)
    check(
        'screenshot_designer',
        what,
        refused and after == before and state_camera.alike(*camera) and '3D view, setting: ' not in t,  # TST-923
        'refused %s, the files back %s, the camera %s then %s | %s'
        % (refused, after == before, state_camera.said(camera[0]), state_camera.said(camera[1]), t.strip()[-200:]),
    )


async def run(ctx: Ctx) -> None:
    c, scratch, G, slope, lv, png = ctx.c, ctx.scratch, ctx.G, ctx.slope, ctx.lv, ctx.png
    # --- Designer facts that GUIDE.md relies on (fail if a Designer update changes them)
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
    t = text(await designer_script(c, 'facts/output_annotations'))
    check(F, 'a new output gets a name of its own', 'DEFAULTS=output,output_1' in t, t)
    check(F, 'two outputs can be given one identifier', 'DUPLICATES_KEPT=True' in t, t)
    check(F, "an identifier's other characters are rewritten", 'REWRITTEN=___a_b_c' in t, t)
    check(
        F, 'the characters apply_edits allows in an identifier are kept', t.count('KEPT ') == 3 and '=False' not in t, t
    )
    check(F, 'a usage tag is taken unchecked', 'USAGE_UNCHECKED=True' in t, t)
    check(F, 'only an output node has an identifier', 'OTHER_NODE_RAISES=True' in t, t)
    # what a rename reaches (GUIDE.md, Output nodes). A pixel, not only the link: a closed graph's looks untouched
    # (measured: the closed graph's pixel went from 407fbfff to 00000000)
    t = text(
        await designer_script(c, 'facts/rename_output_instance', folder=os.path.join(ctx.scratch, 'rename_output'))
    )
    fine = re.search(r'BEFORE connectors=base link=base pixel=(\w+)', t)
    pixel = fine.group(1) if fine else '?'
    check(
        F,
        'an output renamed: an open graph using it follows, also reloaded',
        all(
            '%s connectors=albedo link=albedo pixel=%s' % (case, pixel) in t
            for case in ('SAME_PACKAGE', 'OTHER_PACKAGE', 'RELOADED')
        )
        and pixel not in ('?', '00000000'),
        t,
    )
    check(
        F,
        'an output renamed: a closed graph using it keeps the old connector and computes black, unmarked',
        'CLOSED connectors=base link=base pixel=00000000' in t and 'CLOSED_MARKED_MODIFIED=False' in t,
        t,
    )
    check(
        F,
        'an output renamed: a new instance repairs a closed graph that broke',
        'REPAIRED_BY_NEW_INSTANCE connectors=albedo link=albedo pixel=%s' % pixel in t,
        t,
    )
    check(
        F,
        'an output renamed: renaming back, that graph open, loses the connector and link',
        'REPAIRED_BY_OLD_NAME connectors= link= pixel=00000000' in t,
        t,
    )
    await check_function_graph_states(ctx)
    await check_compute_takes_a_fixed_time(ctx)
    # a graph's model is the same through a save and a reload, so a diff against a saved file reports no change
    # (REVIEW.md SRV-70)
    first, second = os.path.join(scratch, 'round_trip_1.sbs'), os.path.join(scratch, 'round_trip_2.sbs')
    await designer_script(c, 'facts/save_round_trip', graph=TEST_GRAPH, first=first, second=second)
    from server_tools.snapshots import _graph_model

    one, two = _graph_model(first, TEST_GRAPH), _graph_model(second, TEST_GRAPH)
    differing = [key for key in one if one[key] != two[key]]  # type: ignore[literal-required]
    nodes: list[tuple[str, str, object, object]] = [
        (node, field, one['nodes'][node][field], two['nodes'][node][field])  # type: ignore[literal-required]
        for node in one['nodes']
        if node in two['nodes']
        for field in one['nodes'][node]
        if one['nodes'][node][field] != two['nodes'][node][field]  # type: ignore[literal-required]
    ]
    # what the comparison covers, or it would pass on a graph with nothing in it to change (REVIEW.md TST-231)
    levels = [n for n in one['nodes'].values() if n['params'].get('levelinhigh')]
    covers = (
        'floor' in one['inputs'] and len(levels) == 1 and "reads 'floor'" in levels[0]['params'].get('leveloutlow', '')
    )
    check(
        F,
        "a graph's model is the same after a save and a reload",
        covers and not differing,
        '%s %s; a value, an input and a function compared: %s' % (differing, nodes[:2], covers),
    )
    # an int on an enum parameter is accepted whatever it is, and one beyond the enum's can't be read back: why
    # remove_graph_input checks first (GUIDE.md; REVIEW.md HLP-73)
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
    stored: dict[str, tuple[list[str | None], list[str | None]]] = {}
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
    # a node's default is its own: an instance with no input stores nothing for relative to parent (REVIEW.md TST-222)
    instance_stored: dict[str, list[str | None]] = {}
    for name in ('Absolute', 'RelativeToInput', 'RelativeToParent'):
        outer = next(
            g
            for g in ET.parse(os.path.join(inherit_dir, 'instance_%s.sbs' % name)).getroot().iter('graph')
            if g.find('identifier').get('v') == 'mcp_selftest_inherit_outer'  # type: ignore[union-attr]
        )
        instance_stored[name] = [
            p.find('relativeTo').get('v')  # type: ignore[union-attr]
            for p in outer.iter('parameter')
            if p.find('name').get('v') == 'outputsize' and p.find('relativeTo') is not None  # type: ignore[union-attr]
        ]
    check(
        F,
        '.sbs size inheritance: an instance with no input stores nothing for its default, relative to parent',
        instance_stored == {'Absolute': ['0'], 'RelativeToInput': ['2'], 'RelativeToParent': []}
        and 'instance default RelativeToParent' in t,
        '%s %s' % (instance_stored, t),
    )
    # REVIEW.md TST-3: the remaining GUIDE.md facts, measured
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
    await check_unsaved_bitmap_copies(ctx)
    await check_the_largest_output_size(ctx)
    await check_a_blend_opacity_fed_a_colour_image(ctx)
    await check_a_blend_of_a_grey_image_and_a_colour_one(ctx)
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
            bool(along_y > 2 * along_x),
            'mean step along x %.2f, along y %.2f' % (along_x, along_y),
        )
    else:
        check(F, 'anisotropic noise streaks run horizontally by default', False, text(r_))
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': aniso}], **G})
    # exposing a parameter logs these until the function node is named (both in this graph, which has an output node;
    # read_designer_log's docstring says no more of the first than that it may be logged, REVIEW.md TST-246): count
    # each message before and after an exposure made here, so earlier lines can't satisfy the check (REVIEW.md TST-13:
    # it once compared against a header it could never match)
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
    # the preparation opens the graph, so a Designer the self-test started shows its 3D view; only the user's own
    # layout may hide it (REVIEW.md TST-229: skipped whatever the answer, it was skipped in every run)
    hidden = 'NO_3D_VIEW' in t or 'not visible' in text(render)
    if hidden and ctx.was_running:
        skip(F, 'widget capture of the 3D view is not the render', "no 3D View visible in the user's Designer")
    elif hidden or not is_image(render):
        check(F, 'widget capture of the 3D view is not the render', False, '%s / %s' % (t.strip(), text(render)[:200]))
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
    t_gl = text(await c('node_stats', {'node_id': nrm, 'points': [[256, 256]], **G}))
    await c('apply_edits', {'ops': [{'op': 'set', 'node': nrm, 'params': {'inversedy': False}}], **G})
    t_dx = text(await c('node_stats', {'node_id': nrm, 'points': [[256, 256]], **G}))
    # an answer with no pixel fails this check alone, not the rest of the category (REVIEW.md HLP-100)
    gl, dx = pixel_values(t_gl).get((256, 256)), pixel_values(t_dx).get((256, 256))
    # a full-height ramp is a gentle slope (G about 0.49 vs 0.51); the sign is what matters
    check(
        F,
        'normal inversedy=True is OpenGL',
        gl is not None and dx is not None and gl[1] < 0.497 and dx[1] > 0.503 and abs(gl[1] + dx[1] - 1) < 0.002,
        'OpenGL G=%.3f, DirectX G=%.3f' % (gl[1], dx[1]) if gl and dx else '%s / %s' % (t_gl[:150], t_dx[:150]),
    )
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': grad}, {'op': 'delete', 'node': nrm}], **G})
    await check_curvature_smooth_takes_the_format_of_its_normals(ctx)
    # a Dot node (passthrough) has no ID property: Designer's UI portals store it as <userId> in the
    # file and in Designer's memory, not exposed to the API, so the API can't make one (server_tools/layout.py). Any id-like property here would be new
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
    await check_a_packages_uid_survives_saving_and_a_restamped_one_loads(ctx)
    # the 3D view's own state file (ROADMAP item 131), its view put back after each; last, as one raising on a format
    # it doesn't know ends the category's run (REVIEW.md TST-898)
    await check_the_3d_views_state_file_is_saved_and_loaded_in_designers_own_home_showing_nothing(ctx)
    await check_a_3d_shots_set_up_is_designers_state_as_it_renders(ctx)
    await check_the_state_files_rotation_is_in_turns_and_its_intensity_the_exposure(ctx)
    await check_a_dropped_maps_url_is_the_one_the_set_up_writes(ctx)
    await check_the_scene_menus_mesh_switch_frames_the_mesh_from_the_cameras_direction(ctx)
    await check_a_state_file_with_another_mesh_loads_it_keeping_the_files_camera(ctx)
    await check_a_load_of_a_mesh_of_the_users_own_ends_once_the_view_settled(ctx)
    await check_a_state_file_with_one_field_edited_loads_that_field_alone(ctx)
    await check_a_state_file_missing_its_lights_loads_them_at_designers_defaults(ctx)
    await check_reset_scene_reads_the_state_file_once_it_has_returned(ctx)
    await check_designers_frame_gives_the_view_tables_poses(ctx)
    await check_after_a_load_the_3d_view_follows_the_graph_once_another_graph_and_it_are_opened(ctx)
    await check_a_state_file_load_resets_the_aov_and_keeps_the_renderer_and_displacement(ctx)
    await check_a_state_file_load_turns_override_material_on_though_the_file_holds_it_off(ctx)
    await check_a_3d_shot_puts_the_users_3d_view_and_default_state_file_back(ctx)
    await check_a_3d_shot_puts_a_leftover_backup_back_first(ctx)
    await check_a_3d_shot_removes_a_leftover_backup_it_cant_put_back_and_says_so(ctx)
    await check_a_3d_shot_refuses_a_state_file_missing_a_field_and_writes_nothing(ctx)
