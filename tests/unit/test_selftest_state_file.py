"""The pure logic of facts' state file checks (tests/test_all_tools/facts/state_file.py and state_camera.py): the
poses they put and compare, the state file's comparison and the edits of their own, and kept's put-back with a fake
Designer (REVIEW.md TST-889, TST-890, TST-896 to TST-898, TST-903, TST-908 and TST-910, which its tests cite). The
camera's decode and moves, the edits of the fields the set-up sets and the backup are state3d.py's own:
test_state3d.py. The fixture is a state file a Designer just started saved, edited by hand: its home's path is
shortened, and a renderer plugin's section is added with its material's entry, as a later Save wrote it (2026-11-27),
its shading parameters cut to two (REVIEW.md TST-979, TST-983)."""

import ast
import asyncio
import inspect
import math
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from selftest_fakes import code_of, fresh, tool_result

from conftest import FIXTURES, SELFTEST_DIR
from project_constants import ToolArgs

SAVED = Path(FIXTURES, 'state_file.sbsscn').read_text(encoding='utf-8')


@pytest.fixture
def camera() -> ModuleType:
    return fresh('facts.state_camera')


@pytest.fixture
def state() -> ModuleType:
    return fresh('facts.state_file')


@pytest.mark.parametrize('a, b, off', [(179, -179, 2), (10, 370, 0), (-170, 170, 20), (0, 180, 180)])
def test_angles_apart_are_measured_across_the_turn(camera: ModuleType, a: float, b: float, off: float) -> None:
    assert math.isclose(camera.angle_off(a, b), off, abs_tol=1e-9)


def test_poses_turned_apart_add_their_yaws_and_pitches_apart(camera: ModuleType) -> None:
    one = camera.state3d.Pose((0.0, 0.0, 0.0), 175.0, 100.0, 1.0)
    other = camera.state3d.Pose((5.0, 5.0, 5.0), -175.0, 95.0, 2.0)
    assert math.isclose(camera.turned_apart(one, other), 15)


@pytest.mark.parametrize(
    'change, alike',
    [
        ({}, True),
        ({'yaw': 45.005}, True),
        ({'yaw': 45.02}, False),
        ({'pitch': 30.02}, False),
        ({'distance': 100.005}, True),
        ({'distance': 100.02}, False),
        ({'target': (0.02, 50.0, 0.0)}, False),
        ({'target': (0.0, 50.005, 0.0)}, True),
    ],
    ids=[
        'equal',
        'yaw 0.005',
        'yaw 0.02',
        'pitch 0.02',
        'distance 5e-5',
        'distance 2e-4',
        'target 2e-4',
        'target 5e-5',
    ],
)
def test_two_poses_are_alike_within_a_hundredth_of_a_degree_and_1e_4_of_the_distance(
    camera: ModuleType, change: dict[str, float | tuple[float, float, float]], alike: bool
) -> None:
    # REVIEW.md TST-925: the pass criterion of the put-back's checks; lengths in fractions of the distance, 100 here
    pose = camera.state3d.Pose((0.0, 50.0, 0.0), 45.0, 30.0, 100.0)
    assert camera.alike(pose, pose._replace(**change)) is alike


def test_a_pose_is_said_to_2_digits_and_its_distance_to_3(camera: ModuleType) -> None:
    pose = camera.state3d.Pose((1.0, 50.004, -0.5), 45.0000024, 29.9999973, 180.992477)
    assert camera.said(pose) == 'yaw 45.00 pitch 30.00 at (1.00, 50.00, -0.50) from 180.992'


def test_away_puts_the_camera_at_away_looking_at_the_same_point_from_as_far(camera: ModuleType) -> None:
    got = camera.pose(camera.away(SAVED))
    assert (round(got.yaw, 4), round(got.pitch, 4)) == camera.AWAY
    assert [round(v, 4) for v in got.target] == [0, 50, 0] and round(got.distance, 4) == 180.9925


def test_turned_puts_the_camera_at_the_pose_a_load_glides_to(camera: ModuleType) -> None:
    got = camera.pose(camera.turned(SAVED))
    assert (round(got.yaw, 4), round(got.pitch, 4)) == camera.GLIDES_TO
    assert round(got.distance, 4) == round(180.992477 * 1.25, 4)
    assert [round(v, 4) for v in got.target] == [0, 50, 0]


def test_a_pair_printed_is_read_as_two_numbers(state: ModuleType) -> None:
    assert state.pair('PAN=0.0,-1e-05\nORBIT=30.15', 'PAN') == (0.0, -1e-05)


@pytest.mark.parametrize('printed', ['PAN=30.15', 'PAN=1,2,3', 'ORBIT=1,2'], ids=['one', 'three', 'none'])
def test_a_pair_is_refused_unless_two_numbers_are_printed(state: ModuleType, printed: str) -> None:
    with pytest.raises(RuntimeError, match='two numbers'):
        state.pair(printed, 'PAN')


def test_fields_are_read_by_path_a_repeated_tag_numbered(state: ModuleType) -> None:
    assert state.fields('<r><a>1</a><b><a>2</a></b><a> 3 </a></r>') == {'/a': '1', '/b/a': '2', '/a#2': '3'}


@pytest.mark.parametrize(
    'a, b, alike',
    [
        ('float(1)', 'float(1.00001)', True),
        ('float(1)', 'float(1.01)', False),
        ('list(1,2.0000001e-8)', 'list(1,0)', True),
        ('float(1)', 'int(1)', False),
        ('true', 'false', False),
    ],
)
def test_two_values_are_alike_to_their_numbers_rounding(state: ModuleType, a: str, b: str, alike: bool) -> None:
    assert state._alike(a, b) is alike


def test_differing_lists_the_fields_changed_or_held_by_one_file_alone(state: ModuleType) -> None:
    assert state.differing('<r><a>1</a><b>2</b></r>', '<r><a>1.5</a><c>2</c></r>') == ['/a', '/b', '/c']


def test_an_edit_replaces_its_field(state: ModuleType) -> None:
    assert state.edited('<r><a>1</a></r>', '<a>1</a>', '<a>2</a>') == '<r><a>2</a></r>'


@pytest.mark.parametrize('content', ['<r><b/></r>', '<r><a>1</a><a>1</a></r>'], ids=['none', 'twice'])
def test_an_edit_is_refused_unless_its_field_is_there_once(state: ModuleType, content: str) -> None:
    with pytest.raises(RuntimeError, match='matched'):
        state.edited(content, '<a>1</a>', '<a>2</a>')


def test_each_edit_of_one_field_changes_its_field_alone(state: ModuleType) -> None:
    changed = {row.name: state.differing(SAVED, row.edit(SAVED)) for row in state.ONE_FIELD}
    assert changed['environment rotation'] == ['/database/scene/entities/_5/components/display/dome/rotation_angle']
    assert changed['environment exposure'] == ['/database/scene/entities/_5/components/display/intensity']
    assert changed['tiling'] == ['/database/materials/materials/_1/material/parameters/___usd___tiling']
    assert changed['environment map'] == [
        '/database/scene/entities/_5/components/display/environment_texture',
        '/database/scene/entities/_5/components/display/panorama_texture',
        '/database/scene_textures/environment',
        '/database/scene_textures/panorama',
    ]
    assert changed['mesh'] == ['/database/scene/external_scenes/_1/id']
    assert changed['shader model'] == ['/database/plugins/HdEclairRendererPlugin/materials/_1/definition/name']
    assert changed['camera'] == [
        '/database/scene/entities/_1/components/camera/dist_to_target',
        '/database/scene/entities/_1/components/location/local_transform',
    ]


def test_a_mesh_loaded_may_move_the_cameras_clip_planes(state: ModuleType) -> None:
    # REVIEW.md TST-978: from the Plane to the Sphere, the camera's automatic clip planes moved with the mesh's size, a
    # session another category left on the Plane failing the row (measured 2026-11-27)
    mesh = next(row for row in state.ONE_FIELD if row.name == 'mesh')
    written = mesh.edit(SAVED)
    after = written.replace('float(4.7194972)', 'float(2.5)').replace('float(5351.90039)', 'float(2800)')
    assert after.count('clip_plane>float(') == written.count('clip_plane>float(') == 2 and after != written
    assert state.not_loaded(state.differing(SAVED, written), written, after, mesh.follows) == []


def test_the_cameras_row_is_the_last_of_one_fields_rows(state: ModuleType) -> None:
    # the check expects a camera the row turns to be on its way at the load's end, and the others' where it was: a row
    # after the camera's loads the base's camera back, which jumped there (measured 2026-11-27)
    assert state.ONE_FIELD[-1].name == 'camera'


def test_a_field_edited_that_a_load_put_back_is_reported_though_it_follows_others(state: ModuleType) -> None:
    # TST-889: the mesh row's `follows` covers the field it edits, so a load that kept the old mesh passed
    mesh = next(row for row in state.ONE_FIELD if row.name == 'mesh')
    written = mesh.edit(SAVED)
    kept_old_mesh = SAVED.replace('/root/Rounded_Cube/Mesh', '/root/Rounded_Cube/Mesh2')  # a follower changed too
    changed = state.differing(SAVED, written)
    assert state.not_loaded(changed, written, kept_old_mesh, mesh.follows) == ['/database/scene/external_scenes/_1/id']
    # a follower changing alone isn't a field left unloaded
    followed = written.replace('/root/Rounded_Cube/Mesh', '/root/sphere')
    assert state.not_loaded(changed, written, followed, mesh.follows) == []


REFUSED = (  # _sf_path's refusal, as the tool call gives it back
    "RuntimeError: the state file /Users/u/Library/16.0/user_view3d_settings.sbsscn isn't in the Designer's own home ''"
)


def run_kept(
    state: ModuleType,
    tmp_path: Path,
    body: Callable[[str], None] | None = None,
    located: str = '',
    load: str = 'LOADED=True',
    raising: bool = False,
) -> None:
    """kept, its body calling `body` with the state file's path, with a fake Designer: it says where its state file is
    (or `located`), a Save writes the file, and a load says `load`, or raises when `raising`."""
    path = state_path(tmp_path)

    async def c(name: str, args: ToolArgs | None = None) -> SimpleNamespace:
        code = code_of(args)
        if code.endswith("print('PATH=' + _sf_path())"):
            return tool_result(located or 'PATH=' + path)
        if code.endswith('_sf_load()'):
            if raising:
                raise RuntimeError('the bridge went away')
            return tool_result(load)
        if code.endswith('_sf_save()'):
            Path(path).write_text('<saved/>', encoding='utf-8')
        return tool_result('')

    async def go() -> None:
        async with state.kept(state.Ctx(c=c, s=None, scratch=str(scratch), helper_source='', was_running=False)):
            if body is not None:
                body(path)

    scratch = tmp_path / 'scratch'
    scratch.mkdir(exist_ok=True)
    asyncio.run(go())


def state_path(tmp_path: Path) -> str:
    """The state file's path in a Designer's own home in `tmp_path`."""
    return str(tmp_path / 'home' / 'Library' / '16.0' / 'user_view3d_settings.sbsscn')


@pytest.fixture
def path(tmp_path: Path) -> str:
    """The state file's path in a Designer's own home, its folder made."""
    os.makedirs(os.path.dirname(state_path(tmp_path)))
    return state_path(tmp_path)


def edit(path: str) -> None:
    Path(path).write_text('edited', encoding='utf-8')


def test_kept_leaves_no_state_file_where_it_found_none(state: ModuleType, tmp_path: Path, path: str) -> None:
    run_kept(state, tmp_path, edit)
    assert not os.path.exists(path) and not os.path.exists(state.state3d._state_resources(path))


def test_kept_puts_back_the_state_file_and_textures_it_found(state: ModuleType, tmp_path: Path, path: str) -> None:
    Path(path).write_text('<found/>', encoding='utf-8')
    folder = state.state3d._state_resources(path)
    Path(folder).mkdir()
    Path(folder, 'default_baseColor.png').write_bytes(b'png')

    def body(path: str) -> None:
        edit(path)
        Path(folder, 'default_baseColor.png').unlink()

    run_kept(state, tmp_path, body)
    assert Path(path).read_text(encoding='utf-8') == '<found/>'
    assert Path(folder, 'default_baseColor.png').read_bytes() == b'png'


def test_kept_touches_no_state_file_when_designer_refuses_one_outside_its_home(
    state: ModuleType, tmp_path: Path, path: str
) -> None:
    # TST-890: kept's own refusal, Designer's guard refusing the path. The guard itself, in _sf_path, is pinned live by
    # the entries check's REFUSED_WITH_NO_HOME (REVIEW.md TST-908)
    Path(path).write_text('<the users/>', encoding='utf-8')
    with pytest.raises(RuntimeError, match='own home'):
        run_kept(state, tmp_path, edit, located=REFUSED)
    assert Path(path).read_text(encoding='utf-8') == '<the users/>'
    assert not os.path.exists(tmp_path / 'scratch' / 'state_file_aside')


def test_a_shots_backup_is_in_the_state_files_folder(state: ModuleType) -> None:
    # REVIEW.md TST-925: Designer's version folder, as scene3d.py makes it
    path = os.path.join('home', 'Library', '16.0', 'user_view3d_settings.sbsscn')
    assert state.backup(path) == os.path.join('home', 'Library', '16.0', state.state3d.STATE_BACKUP)


def test_kept_removes_a_shots_backup_before_and_after(state: ModuleType, tmp_path: Path, path: str) -> None:
    # REVIEW.md TST-925: one an earlier check left, then one the body's shot leaves; no other check meets them
    shots = state.backup(path)
    os.makedirs(os.path.join(shots, 'folder'))
    seen: list[bool] = []

    def body(path: str) -> None:
        seen.append(os.path.exists(shots))
        os.makedirs(shots)

    run_kept(state, tmp_path, body)
    assert seen == [False] and not os.path.exists(shots)


@pytest.mark.parametrize('load, raising', [('LOADED=False', False), ('', True)], ids=['not loaded', 'raising'])
def test_kept_puts_back_what_it_found_when_the_end_load_fails_then_says_so(
    state: ModuleType, tmp_path: Path, path: str, load: str, raising: bool
) -> None:
    # TST-897: the file found was put back only after a load that worked
    Path(path).write_text('<found/>', encoding='utf-8')
    with pytest.raises(RuntimeError):
        run_kept(state, tmp_path, edit, load=load, raising=raising)
    assert Path(path).read_text(encoding='utf-8') == '<found/>'


@pytest.mark.parametrize(
    'platform, was_running, skipped',
    [('darwin', False, False), ('darwin', True, True), ('win32', False, True)],
    ids=['macOS', "the user's Designer", 'Windows'],
)
def test_the_state_file_checks_skip_where_designer_has_no_home_of_its_own(
    monkeypatch: pytest.MonkeyPatch, platform: str, was_running: bool, skipped: bool
) -> None:
    # TST-890: off macOS the self-test's Designer, started by it or not, writes the user's own state file. Each name is
    # skipped under the tool it is checked under (REVIEW.md TST-959)
    checks = fresh('facts.checks')
    monkeypatch.setattr(sys, 'platform', platform)
    recorded: list[tuple[str, str]] = []
    monkeypatch.setitem(vars(checks), 'skip', lambda tool, name, why: recorded.append((tool, name)))
    assert checks.skipped_in_users(SimpleNamespace(was_running=was_running), 'a check', shots=['a shot']) is skipped
    assert recorded == ([('designer facts', 'a check'), ('screenshot_designer', 'a shot')] if skipped else [])


def test_the_state_file_checks_run_last_all_together() -> None:
    # TST-898: one raising on a format it doesn't know ends the category's run, and the checks after it never ran;
    # TST-910: one of them before another check would skip it so
    checks = fresh('facts.checks')
    awaited = re.findall(r'await ([\w.]+)\(', inspect.getsource(checks.run))
    ours = [
        name
        for name in awaited
        if name.startswith('check_') and 'state_file' in inspect.getsource(getattr(checks, name))
    ]
    assert len(ours) >= 8 and awaited[-len(ours) :] == ours, awaited[-12:]


def _first_after_reset(script: str) -> str:
    """The first statement of the Designer code `script` after it triggers Reset Scene."""
    after = script.split("_sf_menu('Scene', 'Reset Scene')", 1)[1]
    return next(line for line in after.strip().splitlines() if not line.strip().startswith('#'))


def test_the_entries_check_takes_no_event_passes_for_before_the_load(state: ModuleType) -> None:
    # TST-896: "no mesh yet" read after ten event passes took a time for the load: true only while it takes longer
    assert '_process_events' not in state.ENTRIES and 'LOAD_LEFT_FOR_LATER' not in state.ENTRIES


def test_the_entries_check_reads_the_scene_menu_right_as_the_trigger_returns(state: ModuleType) -> None:
    # REVIEW.md TST-943: the set-up reads it there (scene3d._state_load); a wait for the menu to clear passed a Designer
    # that cleared it a moment later
    first = _first_after_reset(state.ENTRIES)
    assert "LOAD_BEGAN=%s' % (not _sf_meshes())" in first, first


def test_the_import_check_reads_the_materials_menu_right_as_the_trigger_returns_with_no_event_pass(
    state: ModuleType,
) -> None:
    # REVIEW.md TST-990: an event pass first, as view3d._materials_used runs, let box.fbx's and the OBJ's imports end
    # before the read; the read "none in use yet" must come as Reset Scene returns, as ENTRIES' does (TST-896, TST-943)
    first = _first_after_reset(state.IMPORTED)
    assert "AT_TRIGGER=%r' % ([_sf_used(), _sf_meshes()],)" in first, first
    reader = state.STATE.split('def _sf_used(', 1)[1].split('\n\n\n', 1)[0]
    assert '_process_events' not in reader and '_materials_used' not in reader, reader


def test_the_facts_read_the_meshes_the_scene_menu_checks_alone(state: ModuleType) -> None:
    # REVIEW.md TST-958: each checked entry counted as a mesh, where the set-up counts an entry checked since the trigger;
    # Display UVs in 2D View, a Scene entry, on throughout made a load read as never begun. One helper reads the menu,
    # keeping its meshes (view3d.MESHES), as the set-up's scene3d._mesh_shown does
    snippets = [value for value in vars(state).values() if isinstance(value, str)]
    reading = [line.strip() for value in snippets for line in value.splitlines() if "_sf_checked('Scene')" in line]
    assert reading == ["return [m for m in _sf_checked('Scene') if m in MESHES]"], reading


def test_each_state_file_check_skipped_is_skipped_under_the_tool_it_is_checked_under() -> None:
    # REVIEW.md TST-959: in the user's Designer, 11 names checked under 'screenshot_designer' were skipped under
    # 'designer facts'. In each check, a name passed to skipped_in_users, or in its shots=, against its check() call's
    # tool, where both are plain; each name in shots= found checked
    tree = ast.parse(Path(SELFTEST_DIR, 'facts', 'checks.py').read_text(encoding='utf-8'))
    compared, wrong, unseen = 0, [], []
    for function in (node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)):
        calls = [(n.func.id, n) for n in ast.walk(function) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        checked = {
            call.args[1].id: call.args[0].value
            for called, call in calls
            if called == 'check'
            and len(call.args) > 1
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[1], ast.Name)
        }
        for call in (c for called, c in calls if called == 'skipped_in_users'):
            skipped = {a.id: 'designer facts' for a in call.args[1:] if isinstance(a, ast.Name)}
            for shots in (k.value for k in call.keywords if k.arg == 'shots' and isinstance(k.value, ast.List)):
                skipped |= {e.id: 'screenshot_designer' for e in shots.elts if isinstance(e, ast.Name)}
            unseen += [
                (function.name, n) for n, tool in skipped.items() if tool != 'designer facts' and n not in checked
            ]
            compared += len(skipped.keys() & checked.keys())
            wrong += [
                (function.name, n, tool, checked[n]) for n, tool in skipped.items() if checked.get(n, tool) != tool
            ]
    assert compared and wrong == [] and unseen == [], (compared, wrong, unseen)


def test_the_entries_check_takes_the_load_as_ended_only_once_it_has_begun(state: ModuleType) -> None:
    # TST-903: a mesh still checked as the trigger returned would have read as the load ended
    after = state.ENTRIES.split("_sf_menu('Scene', 'Reset Scene')", 1)[1]
    began, ended = after.index('not _sf_meshes()'), after.index('bool(_sf_meshes())')
    assert began < ended and 'LOAD_BEGAN' in state.ENTRIES_SAID
