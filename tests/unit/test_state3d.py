"""The 3D view's state file in code (designer_helpers/state3d.py): the fields the tools set, read and edited in a state
file's text, the rest of it kept byte for byte; the camera's pose and moves; and the backup of the file and its
textures' folder, put back (REVIEW.md TST-900, TST-902, TST-914, TST-915, HLP-257 and HLP-263, which its tests
cite). The fixture is a state file a Designer
just started saved (test_selftest_state_file.py). The part takes only the standard library's names from the other
parts, so it runs here as a module of its own (designer_helpers.standalone)."""

import builtins
import math
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, get_args

import pytest
from windows_simulation import _open_as_on_windows

import designer_helpers
from conftest import FIXTURES, with_added_material

if TYPE_CHECKING:  # for the checker: the part as the helpers hold it
    from designer_helpers import state3d
    from designer_helpers.state3d import StateField, StateFields
else:
    state3d = designer_helpers.standalone('state3d')

SAVED = Path(FIXTURES, 'state_file.sbsscn').read_text(encoding='utf-8')
# the fixture's camera, as Designer saved it: the matrix by rows X, Y, Z and the position, then the distance
MATRIX = (
    '0.707106709,0,-0.707106769,0,-0.353553414,0.866025448,-0.353553325,0,0.612372458,0.49999997,0.612372398,0,'
    '110.834808,140.496231,110.834808,1'
)
DISTANCE = '<dist_to_target>float(180.992477)</dist_to_target>'
DEFAULT = (MATRIX, '180.992477')  # the fixture's camera, matrix and distance: Designer's Default view
# other cameras Designer saved (2026-11-25)
OVER_THE_POLE = (  # loaded at yaw 0, pitch 100
    '1,0,-0,0,0,-0.173648179,-0.98480773,0,-0,0.98480773,-0.173648179,0,0,147.721161,-26.047226,1',
    '150',
)
UNDER_THE_POLE = (  # loaded at yaw 30, pitch -100
    '0.866025388,0,-0.5,0,0.492403865,-0.173648179,0.852868557,0,-0.0868240893,-0.98480773,-0.150383726,0,'
    '-13.023613,-147.721161,-22.55756,1',
    '150',
)
TOP = (  # Camera > Top, then Frame, on the Plane
    '1,0,-0,0,-0,5.96046448e-08,-0.99999994,0,0,0.99999994,5.96046448e-08,0,0,147.779694,8.80835705e-06,1',
    '147.779709',
)
MAP = '[(loaderType)(file)][(file)(%s)]'  # an environment's map, as the file holds it
PANORAMA = MAP % 'sd-3dview-maps://panorama_map.hdr'
ENVIRONMENT_PLACES = ('panorama', 'environment', 'panorama_texture', 'environment_texture')


def replaced(content: str, *changes: tuple[str, str]) -> str:
    """`content` with the first of each (old, new) replaced: the text an edit is to give."""
    for old, new in changes:
        assert old in content, old
        content = content.replace(old, new, 1)
    return content


def with_camera(matrix: str, distance: str) -> str:
    """The fixture with its camera's matrix and distance as Designer saved them."""
    return replaced(SAVED, (MATRIX, matrix), (DISTANCE, '<dist_to_target>float(%s)</dist_to_target>' % distance))


def pose_of(content: str) -> 'state3d.Pose':
    return state3d._state_fields(content, ['camera'])['camera']


def off(a: float, b: float) -> float:
    """How far apart two angles in degrees are, across the turn."""
    return abs((a - b + 180) % 360 - 180)


def test_each_field_the_tools_set_has_its_value_and_its_places() -> None:
    # StateField names the fields, StateFields types their values and _PLACES finds them in the file
    assert get_args(state3d.StateField) == tuple(state3d.StateFields.__annotations__) == tuple(state3d._PLACES)


def test_the_fields_the_tools_set_are_read_as_a_saved_file_holds_them() -> None:
    got = state3d._state_fields(SAVED)
    camera = got.pop('camera')
    assert got == {
        'mesh': 'Rounded Cube',
        'tiling': 1,
        'environment': 'sd-3dview-maps://panorama_map.hdr',
        'rotation': 0,
        'exposure': 0,
    }
    assert [round(v, 4) for v in camera.target] == [0, 50, 0]
    assert (round(camera.yaw, 4), round(camera.pitch, 4), camera.distance) == (45, 30, 180.992477)


@pytest.mark.parametrize(
    'fields, changes',
    [
        ({'mesh': 'sphere'}, [('<id>Rounded Cube</id>', '<id>sphere</id>')]),
        # a value at Designer's default, its * dropped as Designer writes a value set
        (
            {'tiling': 2.5},
            [('<___usd___tiling>*float(1)</___usd___tiling>', '<___usd___tiling>float(2.5)</___usd___tiling>')],
        ),
        (
            {'rotation': 0.125},
            [('<rotation_angle>float(0)</rotation_angle>', '<rotation_angle>float(0.125)</rotation_angle>')],
        ),
        ({'exposure': 1 / 3}, [('<intensity>float(0)</intensity>', '<intensity>float(0.333333333)</intensity>')]),
        # the map's four places: the scene's textures, then the Environment entity's. The material's own come after,
        # its panorama alike: the first of each is the one edited
        (
            {'environment': 'sd-3dview-maps://airport.exr'},
            [
                ('<%s>%s</%s>' % (tag, PANORAMA, tag), '<%s>%s</%s>' % (tag, MAP % 'sd-3dview-maps://airport.exr', tag))
                for tag in ENVIRONMENT_PLACES
            ],
        ),
        (
            {'mesh': 'sphere', 'exposure': 1.5},
            [
                ('<id>Rounded Cube</id>', '<id>sphere</id>'),
                ('<intensity>float(0)</intensity>', '<intensity>float(1.5)</intensity>'),
            ],
        ),
    ],
    ids=['mesh', 'tiling', 'rotation', 'exposure', 'environment', 'two at once'],
)
def test_an_edit_writes_its_fields_alone_the_rest_kept_byte_for_byte(
    fields: 'StateFields', changes: list[tuple[str, str]]
) -> None:
    assert state3d._state_edited(SAVED, fields) == replaced(SAVED, *changes)


def test_a_camera_edit_writes_its_matrix_and_distance_alone() -> None:
    at = state3d.Pose((1.0, 2.0, 3.0), 30.0, 10.0, 150.0)
    numbers = ','.join('%.9g' % v for v in state3d._camera_matrix(at))
    got = state3d._state_edited(SAVED, {'camera': at})
    assert got == with_camera(numbers, '150')


def test_text_is_escaped_as_the_file_holds_it_and_read_back() -> None:
    # a map's URL holding brackets, as a path of the user's may: its end is the field's, not the first bracket
    url = 'file:///Users/u/maps/dusk (1) & dawn.hdr'
    got = state3d._state_edited(SAVED, {'mesh': 'a<b>&c', 'environment': url})
    assert '<id>a&lt;b&gt;&amp;c</id>' in got and '(file)(file:///Users/u/maps/dusk (1) &amp; dawn.hdr)]' in got
    read = state3d._state_fields(got, ['mesh', 'environment'])
    assert read == {'mesh': 'a<b>&c', 'environment': url}


@pytest.mark.parametrize(
    'yaw, pitch',
    [(0, 0), (45, 30), (90, 10), (180, 0), (-90, -45), (30, 100), (-60, -120), (0, 90), (30, -90), (10, 179)],
)
def test_a_pose_written_decodes_back(yaw: float, pitch: float) -> None:
    at = state3d.Pose((1.0, 2.0, 3.0), yaw, pitch, 150.0)
    got = pose_of(state3d._state_edited(SAVED, {'camera': at}))
    assert off(got.yaw, yaw) < 1e-4 and off(got.pitch, pitch) < 1e-4
    assert all(abs(a - b) < 1e-4 for a, b in zip(got.target, at.target, strict=True)) and got.distance == 150


@pytest.mark.parametrize(
    'saved, yaw, pitch',
    [(OVER_THE_POLE, 0, 100), (UNDER_THE_POLE, 30, -100), (TOP, 0, 90)],
    ids=['over the pole', 'under the pole', 'Top'],
)
def test_designers_cameras_at_and_beyond_the_pole_decode_as_loaded(
    saved: tuple[str, str], yaw: float, pitch: float
) -> None:
    # TST-900: a decode of Z.y alone read Top at 89.98 degrees
    got = pose_of(with_camera(*saved))
    assert off(got.yaw, yaw) < 1e-4 and abs(got.pitch - pitch) < 1e-4


@pytest.mark.parametrize(
    'saved', [DEFAULT, OVER_THE_POLE, UNDER_THE_POLE, TOP], ids=['Default', 'over', 'under', 'Top']
)
def test_designers_cameras_decoded_are_written_back_as_designer_saved_them(saved: tuple[str, str]) -> None:
    # TST-914: every number of the matrix, Y's own three too, against Designer's, not the code's
    matrix, distance = [float(v) for v in saved[0].split(',')], float(saved[1])
    got = state3d._camera_matrix(state3d._camera_pose(matrix, distance))
    assert all(abs(a - b) < 1e-5 * max(1.0, abs(b)) for a, b in zip(got, matrix, strict=True)), got


def test_a_tilted_camera_is_refused_as_no_pose_of_ours() -> None:
    # TST-902: the decode holds for a camera whose X stays level; one rolled about its own Z would decode wrong
    roll = math.radians(5)
    matrix = [math.cos(roll), math.sin(roll), 0, 0, -math.sin(roll), math.cos(roll), 0, 0, 0, 0, 1, 0, 0, 0, 150, 1]
    with pytest.raises(RuntimeError, match='level'):
        pose_of(with_camera(','.join('%.9g' % v for v in matrix), '150'))


@pytest.mark.parametrize(
    'viewport, distance',
    [((342, 357), 180.992447), ((270, 523), 180.992447), ((567, 373), 251.63411), ((867, 223), 608.54248)],
    ids=['taller than wide', 'much taller', 'wider', 'much wider'],
)
def test_a_view_frames_the_mesh_as_designers_frame_does_at_the_viewports_aspect(
    viewport: tuple[int, int], distance: float
) -> None:
    # the cube framed by Designer's Frame in viewports of these sizes (2026-11-26): no farther while taller than wide
    framed = state3d._framed('cube', 'Front', viewport)
    assert framed.target == (0.0, 50.0, 0.0) and (framed.yaw, framed.pitch) == (0.0, 0.0)
    assert math.isclose(framed.distance, distance, rel_tol=1e-6)


@pytest.mark.parametrize('view', list(state3d.VIEW_DIRECTIONS))
def test_each_view_looks_along_its_direction_at_the_middle_of_the_mesh(view: str) -> None:
    framed = state3d._framed('sd-3dview-shapes://Torus.FBX', view, (400, 400))
    assert (framed.yaw, framed.pitch) == state3d.VIEW_DIRECTIONS[view]
    assert framed.target == state3d.FRAMING['Torus'][1] and framed.distance == state3d.FRAMING['Torus'][2]


def test_a_mesh_switched_to_is_framed_as_frame_frames_it_from_the_cameras_direction() -> None:
    # the Scene menu's switch, measured 2026-11-26 on 6 meshes, docked and wider than tall (the self-test's facts check)
    start = state3d.Pose((10.0, 5.0, -20.0), 30.0, 20.0, 250.0)
    switched = state3d._reframed(start, 'sd-3dview-shapes://Torus.FBX', (667, 343))
    framed = state3d._framed('sd-3dview-shapes://Torus.FBX', 'Front', (667, 343))
    assert switched == framed._replace(yaw=30.0, pitch=20.0)


@pytest.mark.parametrize(
    'asked, changes',
    [
        ({'tiling': 1.0, 'rotation': 0.0, 'exposure': 0.0}, {}),
        ({'environment': 'sd-3dview-maps://panorama_map.hdr', 'mesh': 'Rounded Cube'}, {}),
        # as Designer holds them, 32-bit floats: 1.0000000001 is 1
        ({'tiling': 1.0000000001}, {}),
        (
            {'tiling': 2.0, 'rotation': 0.25, 'exposure': 1.5, 'environment': 'sd-3dview-maps://studio.exr'},
            {'tiling': 2.0, 'rotation': 0.25, 'exposure': 1.5, 'environment': 'sd-3dview-maps://studio.exr'},
        ),
        ({'mesh': 'sphere', 'tiling': 1.0}, {'mesh': 'sphere'}),
    ],
    ids=['the fixtures numbers', 'its map and mesh', 'as held', 'each changed', 'one of two'],
)
def test_the_fields_asked_that_the_file_holds_otherwise_are_its_changes(
    asked: 'StateFields', changes: 'StateFields'
) -> None:
    # a value the view shows already changes nothing (REVIEW.md HLP-195)
    held = state3d._state_fields(SAVED, ['mesh', 'tiling', 'environment', 'rotation', 'exposure'])
    assert state3d._state_changes(held, asked) == changes


def test_a_value_designer_holds_as_a_32_bit_float_is_no_change() -> None:
    # Designer holds the tiling, the rotation and the exposure as 32-bit floats, and saves them so: 2.3 written comes
    # back 2.29999995 (measured 2026-11-26; the self-test's facts check of the units). Asked again, each changes nothing
    saved = replaced(
        SAVED,
        ('<___usd___tiling>*float(1)</___usd___tiling>', '<___usd___tiling>float(2.29999995)</___usd___tiling>'),
        ('<rotation_angle>float(0)</rotation_angle>', '<rotation_angle>float(0.300000012)</rotation_angle>'),
        ('<intensity>float(0)</intensity>', '<intensity>float(0.699999988)</intensity>'),
    )
    held = state3d._state_fields(saved, ['tiling', 'rotation', 'exposure'])
    assert state3d._state_changes(held, {'tiling': 2.3, 'rotation': 0.3, 'exposure': 0.7}) == {}
    assert state3d._state_changes(held, {'tiling': 2.31}) == {'tiling': 2.31}


def test_a_mesh_the_table_lacks_is_framed_as_the_cube() -> None:
    # a mesh of the user's own, its file's URL as the state file holds it (the user, 2026-11-25)
    assert state3d._framed('file:///Users/u/mine.fbx', 'Top', (400, 300)) == state3d._framed('cube', 'Top', (400, 300))


def test_the_meshes_framed_are_the_scene_menus_each_with_its_id() -> None:
    ids = [mesh_id for mesh_id, _, _ in state3d.FRAMING.values()]
    assert len(set(ids)) == len(ids) == 11 and ids[:5] == ['cube', 'cylinder', 'plane', 'plane_hires', 'sphere']


def project(folder: Path, view3d: str) -> None:
    """A user_project.sbsprj in `folder` whose preferences hold `view3d` (an element's text, '' for none)."""
    Path(folder, 'user_project.sbsprj').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<root>\n\t<preferences>\n%s\t\t<library/>\n\t</preferences>\n</root>\n'
        % view3d,
        encoding='utf-8',
    )


def test_the_default_state_file_is_the_version_folders_own_with_no_default_state_file_set(tmp_path: Path) -> None:
    project(tmp_path, '')
    assert state3d._state_default_path(str(tmp_path)) == str(tmp_path / 'user_view3d_settings.sbsscn')
    os.remove(tmp_path / 'user_project.sbsprj')  # none written yet
    assert state3d._state_default_path(str(tmp_path)) == str(tmp_path / 'user_view3d_settings.sbsscn')


def test_the_users_default_state_file_is_the_one_their_project_settings_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Project settings > 3D View: the URL as Designer read it (measured 2026-11-26), XML escaping included. Read as
    # POSIX reads it, as the Windows test reads it as Windows does (REVIEW.md TST-926)
    import urllib.parse
    import urllib.request

    monkeypatch.setattr(urllib.request, 'url2pathname', urllib.parse.unquote)
    project(
        tmp_path,
        '\t\t<view3d>\n\t\t\t<stateSaveFileUrl>file:///a b/R&amp;D/s.sbsscn</stateSaveFileUrl>\n\t\t</view3d>\n',
    )
    assert state3d._state_default_path(str(tmp_path)) == '/a b/R&D/s.sbsscn'


def test_a_windows_default_state_file_url_is_read_as_windows_reads_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # REVIEW.md HLP-266: the standard Windows form holds the drive after a third slash, read as /C:/... before. The
    # form Designer writes on Windows isn't measured (ROADMAP item 90); Windows' own reading, nturl2path's, is taken
    import nturl2path
    import urllib.request

    monkeypatch.setattr(urllib.request, 'url2pathname', nturl2path.url2pathname)
    project(
        tmp_path,
        '\t\t<view3d>\n\t\t\t<stateSaveFileUrl>file:///C:/Users/me/My%20Files/s.sbsscn</stateSaveFileUrl>\n'
        '\t\t</view3d>\n',
    )
    assert state3d._state_default_path(str(tmp_path)) == 'C:\\Users\\me\\My Files\\s.sbsscn'


def test_a_default_state_file_set_otherwise_than_as_a_file_url_is_refused(tmp_path: Path) -> None:
    # the file Designer then saves isn't known, so it would be written with no backup
    project(tmp_path, '\t\t<view3d>\n\t\t\t<stateSaveFileUrl>/a/s.sbsscn</stateSaveFileUrl>\n\t\t</view3d>\n')
    with pytest.raises(RuntimeError, match=r"Default State File '/a/s\.sbsscn' isn't a file URL"):
        state3d._state_default_path(str(tmp_path))


@pytest.mark.parametrize('zoom, distance', [(2, 81.0), (-3, 133.1), (0, 100.0)])
def test_the_moves_turn_then_pan_along_the_turned_camera_then_zoom(zoom: int, distance: float) -> None:
    front = state3d.Pose((0.0, 0.0, 0.0), 0.0, 0.0, 100.0)
    got = state3d._camera_moved(front, (400.0, 200.0), (90.0, 0.0), (0.25, 0.5), zoom)
    assert (got.yaw, got.pitch) == (90, 0)
    # turned to Right, the camera's X is -z: a quarter of a view's width right, then half its height up (in widths)
    want = (0.0, state3d.PAN_RATE * 100 * 0.5 * 200 / 400, -state3d.PAN_RATE * 100 * 0.25)
    assert all(abs(a - b) < 1e-9 for a, b in zip(got.target, want, strict=True))
    assert math.isclose(got.distance, distance)


def test_an_orbit_up_from_a_pitched_camera_raises_it_by_its_degrees() -> None:
    # TST-914: from Default (pitch 30), the moves' other tests turning with up at 0
    got = state3d._camera_moved(pose_of(SAVED), (400.0, 200.0), (0.0, 20.0), (0.0, 0.0), 0)
    assert math.isclose(got.yaw, 45, abs_tol=1e-4) and math.isclose(got.pitch, 50, abs_tol=1e-4)


def test_a_pan_up_from_a_pitched_camera_moves_the_point_along_the_cameras_own_up() -> None:
    # TST-914: Designer's camera at Default, pitched 30 degrees: its Y row as saved is the way up, not the world's y
    start, up = pose_of(SAVED), [float(v) for v in MATRIX.split(',')[4:7]]
    got = state3d._camera_moved(start, (400.0, 200.0), (0.0, 0.0), (0.0, 0.5), 0)
    by = state3d.PAN_RATE * start.distance * 0.5 * 200 / 400  # half the view's height, in widths
    want = [t + by * u for t, u in zip(start.target, up, strict=True)]
    assert all(abs(a - b) < 1e-3 for a, b in zip(got.target, want, strict=True)), got.target


def test_a_turn_right_over_the_pole_turns_the_yaw_the_other_way() -> None:
    # TST-902: the camera upside down, the view's right is the other way round (measured: from yaw 45, pitch 119.95,
    # 30.15 degrees right gave yaw 14.85)
    over = state3d.Pose((0.0, 0.0, 0.0), 45.0, 119.95, 100.0)
    got = state3d._camera_moved(over, (400.0, 200.0), (30.15, 0.0), (0.0, 0.0), 0)
    assert math.isclose(got.yaw, 14.85) and math.isclose(got.pitch, 119.95)


@pytest.mark.parametrize('version', ['<version>9</version>', '<version>11</version>', ''], ids=['9', '11', 'none'])
def test_a_file_of_another_format_version_is_refused_by_reads_and_edits(version: str) -> None:
    other = replaced(SAVED, ('<version>10</version>', version))
    with pytest.raises(RuntimeError, match='format version'):
        state3d._state_fields(other, ['camera'])
    with pytest.raises(RuntimeError, match='format version'):
        state3d._state_edited(other, {'tiling': 2.5})


@pytest.mark.parametrize(
    'name, fields, lacking, stray',
    [
        ('mesh', {'mesh': 'sphere'}, '<id>Rounded Cube</id>', True),
        # the tiling removed only: one moved out of the used material's entry (_IN_MATERIAL) isn't tried here
        ('tiling', {'tiling': 2.5}, '<___usd___tiling>*float(1)</___usd___tiling>', False),
        ('rotation', {'rotation': 0.5}, '<rotation_angle>float(0)</rotation_angle>', True),
        # the lights' intensities come after the Environment's: the field is the entity's own
        ('exposure', {'exposure': 1.5}, '<intensity>float(0)</intensity>', True),
        # the material's map comes after the scene's textures: the field is theirs
        ('environment', {'environment': 'x'}, '<environment>%s</environment>' % PANORAMA, True),
        ('environment', {'environment': 'x'}, '<environment_texture>%s</environment_texture>' % PANORAMA, True),
        ('camera', {'camera': state3d.Pose((0.0, 0.0, 0.0), 0.0, 0.0, 1.0)}, DISTANCE, True),
    ],
    ids=['mesh', 'tiling', 'rotation', 'exposure', "the scene's map", "the entity's map", 'camera'],
)
def test_a_file_lacking_a_field_an_edit_sets_is_refused_and_so_is_its_read(
    name: 'StateField', fields: 'StateFields', lacking: str, stray: bool
) -> None:
    # the other field edited with it isn't written either: nothing is. TST-914: with `stray`, the element is moved to
    # the end of the database, outside the one that holds the field, where the place's bound keeps it from being taken
    content = replaced(SAVED, (lacking, ''))
    if stray:
        content = replaced(content, ('</database>', lacking + '</database>'))
    with pytest.raises(RuntimeError, match='%s.* 0 times' % name):
        state3d._state_edited(content, {'rotation': 0.25, **fields})
    with pytest.raises(RuntimeError, match='%s.* 0 times' % name):
        state3d._state_fields(content, [name])


WITH_UNUSED = with_added_material(SAVED)


def test_the_tiling_is_the_material_the_mesh_uses_an_unused_one_left_as_it_is() -> None:
    # REVIEW.md HLP-114, HLP-280: material_mapping_table maps each part of the mesh to the material it uses (measured)
    assert state3d._state_fields(WITH_UNUSED, ['tiling']) == {'tiling': 1.0}
    assert state3d._state_edited(WITH_UNUSED, {'tiling': 2.5}) == replaced(
        WITH_UNUSED, ('<___usd___tiling>*float(1)</___usd___tiling>', '<___usd___tiling>float(2.5)</___usd___tiling>')
    )


def test_a_mesh_using_several_materials_is_refused_its_tiling_but_the_others_are_read_and_edited() -> None:
    # tiling= would tile one of them (REVIEW.md TST-315): a part mapped to the added material
    several = replaced(
        WITH_UNUSED,
        (
            '<_7 prefix="_">\n\t\t\t\t\t<material_instance_id>default</material_instance_id>',
            '<_7 prefix="_">\n\t\t\t\t\t<material_instance_id>added</material_instance_id>',
        ),
    )
    refused = r"^the 3D view's mesh uses 2 materials \(added, default\): tiling= sets the material of a mesh with one$"
    with pytest.raises(RuntimeError, match=refused):
        state3d._state_edited(several, {'tiling': 2.5})
    with pytest.raises(RuntimeError, match=refused):
        state3d._state_fields(several, ['tiling'])
    assert state3d._state_fields(several, ['mesh']) == {'mesh': 'Rounded Cube'}
    assert state3d._state_edited(several, {'rotation': 0.25}) == replaced(
        several, ('<rotation_angle>float(0)</rotation_angle>', '<rotation_angle>float(0.25)</rotation_angle>')
    )


def test_the_file_is_written_and_read_byte_for_byte_also_as_windows_writes_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Designer's own line ends kept, whatever the system's. TST-915: a text write as Windows makes it (the Windows
    # simulation's), where one with no `newline` given writes each \n as \r\n; a read on macOS takes \r\n for \n
    monkeypatch.setattr(builtins, 'open', _open_as_on_windows)
    path, content = str(tmp_path / 'state.sbsscn'), '<root>\r\n\t<a>1</a>\n</root>'
    state3d._state_write(path, content)
    assert Path(path).read_bytes() == content.encode('utf-8')
    assert state3d._state_text(path) == content


def state_path(tmp_path: Path) -> str:
    """The state file's path in its version folder in `tmp_path`, the folder made."""
    os.makedirs(tmp_path / '16.0')
    return str(tmp_path / '16.0' / 'user_view3d_settings.sbsscn')


def saved(path: str, content: str, textures: dict[str, bytes]) -> None:
    """The state file `path` and its textures' folder as a Save writes them: the folder only with textures."""
    Path(path).write_text(content, encoding='utf-8')
    shutil.rmtree(state3d._state_resources(path), ignore_errors=True)
    for name, data in textures.items():
        os.makedirs(state3d._state_resources(path), exist_ok=True)
        Path(state3d._state_resources(path), name).write_bytes(data)


def listed(path: str) -> dict[str, bytes] | None:
    """The textures in the folder of `path`; None when there is no folder."""
    folder = state3d._state_resources(path)
    return {f: Path(folder, f).read_bytes() for f in sorted(os.listdir(folder))} if os.path.isdir(folder) else None


def test_the_textures_folder_is_beside_the_file_named_after_it() -> None:
    assert state3d._state_resources(os.path.join('a', 'user_view3d_settings.sbsscn')) == os.path.join(
        'a', 'user_view3d_settings_resources'
    )


def test_the_backup_puts_back_the_file_and_its_textures_as_they_were(tmp_path: Path) -> None:
    path, aside = state_path(tmp_path), str(tmp_path / 'aside')
    saved(path, '<users/>', {'default_baseColor.png': b'png'})
    assert state3d._state_back_up(path, aside) is None  # no backup left before it
    saved(path, '<ours/>', {'default_baseColor.png': b'ours', 'default_normal.png': b'n'})
    assert state3d._state_put_back(aside) is True
    assert Path(path).read_text(encoding='utf-8') == '<users/>' and listed(path) == {'default_baseColor.png': b'png'}
    assert not os.path.exists(aside)
    assert state3d._state_put_back(aside) is False  # put back once


@pytest.mark.parametrize('ours', [{}, {'default_baseColor.png': b'ours'}], ids=['no textures', 'textures'])
def test_with_no_file_the_put_back_leaves_none(tmp_path: Path, ours: dict[str, bytes]) -> None:
    path, aside = state_path(tmp_path), str(tmp_path / 'aside')
    state3d._state_back_up(path, aside)
    saved(path, '<ours/>', ours)
    state3d._state_put_back(aside)
    assert not os.path.exists(path) and listed(path) is None


def test_a_leftover_backup_is_put_back_first(tmp_path: Path) -> None:
    path, aside = state_path(tmp_path), str(tmp_path / 'aside')
    saved(path, '<users/>', {'t.png': b'users'})
    state3d._state_back_up(path, aside)
    saved(path, '<ours, left by a call that never ended/>', {})
    assert state3d._state_back_up(path, aside) == state3d.LEFTOVER_PUT_BACK % path
    assert Path(path).read_text(encoding='utf-8') == '<users/>' and listed(path) == {'t.png': b'users'}
    saved(path, '<ours/>', {})
    state3d._state_put_back(aside)
    assert Path(path).read_text(encoding='utf-8') == '<users/>' and listed(path) == {'t.png': b'users'}


def test_a_leftover_backup_that_records_no_path_is_removed_and_said(tmp_path: Path) -> None:
    # one made before REVIEW.md HLP-257's fix: where it came from isn't known, so it is removed and said (the user,
    # 2026-11-26), and the file as found is backed up
    path, aside = state_path(tmp_path), str(tmp_path / 'aside')
    os.makedirs(aside)
    Path(aside, 'file').write_text('<old/>', encoding='utf-8')
    saved(path, '<users/>', {'t.png': b'users'})
    assert state3d._state_back_up(path, aside) == state3d.LEFTOVER_REMOVED % 'it records no path'
    assert Path(path).read_text(encoding='utf-8') == '<users/>'
    saved(path, '<ours/>', {})
    assert state3d._state_put_back(aside) is True
    assert Path(path).read_text(encoding='utf-8') == '<users/>' and listed(path) == {'t.png': b'users'}


def test_a_leftover_backup_whose_folder_is_gone_is_removed_and_said(tmp_path: Path) -> None:
    # a Default State File's folder removed since (the user, 2026-11-26): nothing is written there
    path, aside, gone = state_path(tmp_path), str(tmp_path / 'aside'), tmp_path / 'project'
    os.makedirs(gone)
    saved(str(gone / 'own.sbsscn'), '<the users own/>', {})
    state3d._state_back_up(str(gone / 'own.sbsscn'), aside)
    shutil.rmtree(gone)
    saved(path, '<users/>', {})
    said = state3d._state_back_up(path, aside)
    assert said == state3d.LEFTOVER_REMOVED % ('the folder it came from is gone: %s' % gone)
    assert not os.path.exists(gone) and not os.path.exists(aside + '~')
    saved(path, '<ours/>', {})
    state3d._state_put_back(aside)
    assert Path(path).read_text(encoding='utf-8') == '<users/>'


def test_a_leftover_backup_goes_back_to_its_own_path_and_the_next_one_is_left_alone(tmp_path: Path) -> None:
    # HLP-257: a call backed up one path and never put it back; the next call's is another (a Default State File set
    # since, a new version folder). The leftover goes back where it came from, and the other path's file is backed up
    # as it was, never written over
    path, aside, other = state_path(tmp_path), str(tmp_path / 'aside'), str(tmp_path / 'project' / 'own.sbsscn')
    os.makedirs(tmp_path / 'project')
    saved(path, '<users/>', {'t.png': b'users'})
    state3d._state_back_up(path, aside)
    saved(path, '<ours, left by a call that never ended/>', {})
    saved(other, '<the users own/>', {'o.png': b'own'})
    assert state3d._state_back_up(other, aside) == state3d.LEFTOVER_PUT_BACK % path
    assert Path(other).read_text(encoding='utf-8') == '<the users own/>' and listed(other) == {'o.png': b'own'}
    assert Path(path).read_text(encoding='utf-8') == '<users/>' and listed(path) == {'t.png': b'users'}
    saved(other, '<ours/>', {})
    state3d._state_put_back(aside)
    assert Path(other).read_text(encoding='utf-8') == '<the users own/>' and listed(other) == {'o.png': b'own'}


def test_a_relative_path_is_put_back_where_it_was_once_the_working_folder_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # HLP-263: the backup records the path as an absolute one, and copies from that same path
    path, aside = state_path(tmp_path), str(tmp_path / 'aside')
    saved(path, '<users/>', {'t.png': b'users'})
    monkeypatch.chdir(os.path.dirname(path))
    state3d._state_back_up(os.path.basename(path), aside)
    saved(path, '<ours/>', {})
    monkeypatch.chdir(tmp_path)
    assert state3d._state_put_back(aside) is True
    assert Path(path).read_text(encoding='utf-8') == '<users/>' and listed(path) == {'t.png': b'users'}


def stopped(*args: object, **kwargs: object) -> NoReturn:
    raise RuntimeError('stopped')  # an abort, landing in the copy


def test_a_backup_stopped_midway_is_never_put_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # the file copied, the folder not: put back, it would remove the folder found
    path, aside = state_path(tmp_path), str(tmp_path / 'aside')
    saved(path, '<users/>', {'t.png': b'users'})
    with monkeypatch.context() as m:
        m.setattr(shutil, 'copytree', stopped)
        with pytest.raises(RuntimeError, match='stopped'):
            state3d._state_back_up(path, aside)
    assert state3d._state_put_back(aside) is False
    assert Path(path).read_text(encoding='utf-8') == '<users/>' and listed(path) == {'t.png': b'users'}
    assert state3d._state_back_up(path, aside) is None  # what it left is not a backup
    saved(path, '<ours/>', {})
    state3d._state_put_back(aside)
    assert listed(path) == {'t.png': b'users'}


def test_a_put_back_stopped_midway_is_done_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path, aside = state_path(tmp_path), str(tmp_path / 'aside')
    saved(path, '<users/>', {'t.png': b'users'})
    state3d._state_back_up(path, aside)
    saved(path, '<ours/>', {'t.png': b'ours'})
    with monkeypatch.context() as m:
        m.setattr(shutil, 'copytree', stopped)
        with pytest.raises(RuntimeError, match='stopped'):
            state3d._state_put_back(aside)
    assert state3d._state_put_back(aside) is True
    assert Path(path).read_text(encoding='utf-8') == '<users/>' and listed(path) == {'t.png': b'users'}
