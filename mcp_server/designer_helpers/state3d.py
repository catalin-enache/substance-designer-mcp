"""The 3D view's own state file (`.sbsscn`, ROADMAP item 131): the fields the tools set, read and edited in its text,
the rest of it kept byte for byte; the camera's pose and its moves; and the backup of the file and its textures'
folder, put back; the pose of a view, framed as Designer's Frame does; the default state file's path. The caller gives
the folders. The part takes only the standard library's names from core, so the tests run it as a module of its own
(designer_helpers.standalone), and facts' state file checks check Designer against this code
(tests/test_all_tools/facts/state_file.py and state_camera.py). scene3d.py drives the file in Designer.

What it relies on, measured on macOS in Designers an agent started (Designer 16.0.7, 2026-11-25), and pinned by those
checks, but for the moves (below):

- The format is version 10 (STATE_VERSION). Each field the tools set (StateField), edited alone, loads alone, and all
  of them edited load in one Reset Scene:
  - `mesh`: the mesh's id in `external_scenes` (`sphere`). A load of another mesh's id keeps the file's camera:
    Designer doesn't frame the new mesh;
  - `tiling`: the `___usd___tiling` of the material the mesh uses. Each material holds one, a material Materials > Add
    added too, which `material_mapping_table` maps no part of the mesh to: the mesh uses the one it maps each part to
    (_used_material). A load with that one's tiling edited tiles the mesh (editor_panels_and_fit's check of an unused
    material);
  - `environment`: the environment's map, as a URL. Each of Designer's own maps is MAP_SCHEME and its file's name, as
    a drop of each of the 34 saved it (`sd-3dview-maps://studio 02.exr`, its space kept), and Save copies no map
    beside the file. Four places hold it, and an edit writes all four: the scene's textures, the lighting's and the
    background's, and the Environment entity's own two;
  - `rotation`: the environment's, the entity's `dome/rotation_angle`, in turns about Y: 0.25 shows as 90 degrees
    in Environment > Edit properties;
  - `exposure`: the entity's `intensity`, which that panel shows as the Exposure;
  - `camera`: the Default Camera entity's `local_transform` and `dist_to_target`.
- A value set is written with no `*` in front, so an edit drops the `*` that marks a value at Designer's default.
- Designer holds the tiling, the rotation and the exposure as 32-bit floats, and saves each to 9 significant digits:
  a tiling of 2.3 written is saved 2.29999995 (_float32).
- The camera's matrix holds its rows X, Y and Z, then its position. The camera looks along -Z, at the point its
  distance away. Its X stays level: its yaw is X's angle, and its pitch is Z's against Y's, at any pitch, over the
  pole too, where Y points down (over the pole: cameras Designer saved, the unit tests' fixtures).
- The set-up's moves from a pose (_camera_moved), the orbit first, then the pan, then the zoom:
  - an orbit turns the camera by its degrees, sideways then up, with no limit. Sideways, a camera pitched or over the
    pole stays level, and over the pole a turn right turns the yaw the other way;
  - a pan right of p of the view's width moves the point looked at PAN_RATE x the distance x p, along the turned
    camera's X. A pan up of p of the view's height moves it as far as that height is in widths, along its Y;
  - a step closer brings the camera to ZOOM_STEP x the distance, and one away to ZOOM_AWAY x it.
  Measured against the drags of the set-up then (2026-11-25). Since, the editor_panels_and_fit checks pin them
  against Designer's own views and the plane's movement in the render: an orbit's turn against Designer's views up to
  the pole, the zoom's steps within 5 %, which tells their count, and a pan after 4 steps away within 2.9 %, which a pan
  rate or a step away 5 % off fails (REVIEW.md TST-919). A camera over the pole, and the yaw's turn there, were
  measured against the drags (2026-11-25) and once more by probe (2026-11-26), and aren't checked (REVIEW.md
  HLP-284).
- Save writes the textures of a graph whose outputs are on the mesh into `<the file's stem>_resources/` beside it
  (_state_resources); with no graph's outputs there, no folder.
- The default state file is STATE_NAME in Designer's version folder, or the user's Default State File, a file URL in
  their project settings (_state_default_path). Designer reads that setting as it starts (2026-11-26, the self-test's
  lifecycle check).
- A view's pose (_framed), measured 2026-11-26 in Designers an agent started, with Designer's default lens:
  - Camera > <view> looks along the view's direction (VIEW_DIRECTIONS). Frame then looks at a point of the mesh's own
    from a distance of its own (FRAMING, _framing), whatever the view: on each of the 11 meshes, Front, Top and Default
    gave one point and distance. A mesh picked in the Scene menu is framed the same way, the camera's direction kept,
    which mesh= does through the file;
  - in a viewport wider than tall, the distance is FRAMING's x sin(FRAME_ANGLE) / sin(FRAME_ANGLE / its width over
    its height). It fitted 17 viewports from 1.07 to 3.89 times as wide as tall within 2e-7 of the distance, and
    taller ones kept FRAMING's. FRAME_ANGLE is 2 atan(18 / 35), the default 35 mm lens across a 36 mm frame;
  - a fresh Designer's own mesh has another id than the Scene menu's Rounded cube (`Rounded Cube`): framed as the
    cube, whose point is the same and whose distance is within 2e-7.
- A backup an earlier call left is put back first, or removed when it records no path or its path's folder is gone
  (_state_back_up; the user, 2026-11-26).

Measured, not checked:
- a load with the used material's tiling edited left the unused one's as it was, and a mesh of another id loaded with
  it was mapped to the same material, the default one (once each, 2026-11-26);
- a value at Designer's default is written with a `*` in front (`*float(1)`, the unit tests' fixture);
- each of the map's four places set the map in a Designer just started. Once a map had been dropped on the view, the
  entity's own two alone didn't (one Designer each);
- a file saved with the GPU Pathtracer set holds each place once, as the Rasterizer's does (once, 2026-11-25).

Not measured:
- a turn sideways from the poles, Top and Bottom, where the yaw's direction would follow a cosine of float noise
  (_camera_moved);
- a turn sideways from below the south pole, a pitch under -90, where _camera_moved turns the yaw the other way, as
  over the north pole;
- a turn up from a camera upside down.
"""

import shutil
import struct
import urllib.request

from .core import ElementTree, Literal, NamedTuple, Sequence, TypedDict, html, math, os, re

STATE_VERSION = '10'  # the format's version, its settingsInfo
STATE_NAME = 'user_view3d_settings.sbsscn'  # the default state file, in Designer's version folder
STATE_BACKUP = 'sd_mcp_3d_view_backup'  # the 3D shot's backup of it, a folder in Designer's version folder
PAN_RATE = 1.021  # x the distance: how far a pan of a view's width moves the point looked at
ZOOM_STEP = 0.9  # x the distance, a step closer
ZOOM_AWAY = 1.1  # x the distance, a step away: not 1 / ZOOM_STEP
CAMERA_LEVEL = 1e-4  # X's y at most, a camera level: Designer's saved 0, or -0 (2026-11-25)
# each view's direction once framed, (yaw, pitch) as _camera_pose decodes it up to the turn's wrap at Back (180 or
# -180): Top and Bottom look straight down and up
VIEW_DIRECTIONS: dict[str, tuple[float, float]] = {
    'Default': (45.0, 30.0),
    'Front': (0.0, 0.0),
    'Right': (90.0, 0.0),
    'Back': (180.0, 0.0),
    'Left': (-90.0, 0.0),
    'Top': (0.0, 90.0),
    'Bottom': (0.0, -90.0),
}
# each mesh of the 3D view's Scene menu, in its order: its id in the state file, then the point Frame looks at and its
# distance there in a viewport no wider than tall, as Designer saved them (2026-11-26)
FRAMING: dict[str, tuple[str, tuple[float, float, float], float]] = {
    'Cube': ('cube', (0.0, 50.0, 0.0), 180.992447),
    'Cylinder': ('cylinder', (0.0, 100.0, 0.0), 255.961975),
    'Plane': ('plane', (0.0, 0.0, 0.0), 147.779709),
    'Plane (hi-res)': ('plane_hires', (0.0, 0.0, 0.0), 147.779709),
    'Sphere': ('sphere', (0.0, 50.0, 0.0), 180.992447),
    'Cloth': ('sd-3dview-shapes://Cloth.fbx', (-0.628599107, 40.1302986, -4.212097), 166.194107),
    'Mat ball': ('sd-3dview-shapes://Mat Ball.FBX', (0.0, 50.4281502, -2.681), 178.221283),
    'Rounded cube': ('sd-3dview-shapes://Rounded Cube.fbx', (0.0, 50.0, 0.0), 180.992477),
    'Rounded cylinder': ('sd-3dview-shapes://Rounded Cylinder.fbx', (0.0, 50.0, 0.0), 174.335876),
    'Sphere 2 tiles': ('sd-3dview-shapes://Sphere 2 Tiles.FBX', (0.0, 50.0, 0.0), 180.992477),
    'Torus': ('sd-3dview-shapes://Torus.FBX', (-0.0128097534, 15.4115238, 0.054932), 151.068176),
}
# radians: in a viewport wider than tall, Frame's distance is FRAMING's x sin(FRAME_ANGLE) / sin(FRAME_ANGLE / its
# width over its height). It is the default 35 mm lens's angle across a 36 mm frame (the module docstring)
FRAME_ANGLE = 2 * math.atan(18 / 35)
MAP_SCHEME = 'sd-3dview-maps://'  # the file names one of Designer's environment maps by it, then the map's file's name
USERS_MESH = 'file://'  # the file names a mesh of the user's own by its file's URL, which the Scene menu doesn't list
# the mesh using other than one material, then their names in brackets: tiling= would set one of them (REVIEW.md
# TST-315). The Materials menu (view3d._material_checked) and the state file (_used_material) tell them
MATERIALS_USED = "the 3D view's mesh uses %d materials%s: tiling= sets the material of a mesh with one"
LEFTOVER_PUT_BACK = "a backup of the 3D view's default state, left by an earlier call, was put back first: %s"
LEFTOVER_REMOVED = (
    "a backup of the 3D view's default state, left by an earlier call, couldn't be put back (%s), and was removed"
)

StateField = Literal['mesh', 'tiling', 'environment', 'rotation', 'exposure', 'camera']  # each one of StateFields
_ValueKind = Literal['float', 'text', 'map', 'matrix']  # each one of _KINDS


class Pose(NamedTuple):
    """The camera, where the tools put it."""

    target: tuple[float, float, float]  # the point the camera looks at
    yaw: float  # degrees: 0 looking along -z (Front), 90 along -x (Right)
    pitch: float  # degrees: up from the horizon, 90 looking down (Top); beyond 90 over the top
    distance: float


class StateFields(TypedDict, total=False):
    """The fields the tools set, read from a state file or written in it."""

    mesh: str  # the mesh's id
    tiling: float
    environment: str  # the environment's map, its URL
    rotation: float  # the environment's, in turns about Y
    exposure: float
    camera: Pose


# What comes before a value's element, inside the element named: `.` takes newlines too, and `(?:(?!</x>).)*?` stays
# inside x, so a value missing there isn't taken from an element after it
_IN_MESH = r'<external_scenes>(?:(?!</external_scenes>).)*?'  # the first scene's: the files measured held one
_IN_SCENE_TEXTURES = r'<scene_textures>(?:(?!</scene_textures>).)*?'
_IN_ENVIRONMENT = r'<name>Environment</name>(?:(?!</components>).)*?'
_IN_CAMERA = r'<name>Default Camera</name>(?:(?!</components>).)*?'
# the materials list's entry of the material of id %s, as the file holds it, escaped as a regex; the mapping table's
# entries follow its id with no <material>
_IN_MATERIAL = r'<material_instance_id>%s</material_instance_id>\s*<material>(?:(?!</material>).)*?'
# Each kind of value: the regex of its text, its group the value's text, and the text written for a value's text. A
# value's text is unescaped once read and escaped to be written, as XML holds text
_KINDS: dict[_ValueKind, tuple[str, str]] = {
    'float': (r'float\(([^)]*)\)', 'float(%s)'),
    'text': (r'([^<]*)', '%s'),
    'map': (r'\[\(loaderType\)\(file\)\]\[\(file\)\((.*?)\)\]', '[(loaderType)(file)][(file)(%s)]'),
    'matrix': (r'list&lt;float&gt;\[16\]\(([^)]*)\)', 'list&lt;float&gt;[16](%s)'),
}
# Each field's places, every field the tools set: its kind there, what comes before the element, and the element's tag
_PLACES: dict[StateField, tuple[tuple[_ValueKind, str, str], ...]] = {
    'mesh': (('text', _IN_MESH, 'id'),),
    'tiling': (('float', '', '___usd___tiling'),),  # in the material the mesh uses (_located, _used_material)
    'environment': (
        ('map', _IN_SCENE_TEXTURES, 'environment'),
        ('map', _IN_SCENE_TEXTURES, 'panorama'),
        ('map', _IN_ENVIRONMENT, 'environment_texture'),
        ('map', _IN_ENVIRONMENT, 'panorama_texture'),
    ),
    'rotation': (('float', _IN_ENVIRONMENT, 'rotation_angle'),),
    'exposure': (('float', _IN_ENVIRONMENT, 'intensity'),),
    'camera': (('matrix', _IN_CAMERA, 'local_transform'), ('float', _IN_CAMERA, 'dist_to_target')),
}


def _state_version_checked(content: str) -> None:
    """Raises unless the state file `content` is of the format version STATE_VERSION."""
    found = re.search(r'<settingsInfo>\s*<version>([^<]*)</version>', content)
    version = found.group(1).strip() if found else None
    if version != STATE_VERSION:
        raise RuntimeError(
            "the 3D view's state file is of format version %s, and only version %s is known: refused"
            % (version or 'none', STATE_VERSION)
        )


def _located(content: str, field: StateField) -> list[re.Match[str]]:
    """Each place of `field` in the state file `content`, its match's groups the text before the value, the value and
    the text after (a `*` before the value outside them). Raises unless the file holds each place once, as found from
    its anchor: the mesh's id is the first in `external_scenes`, and the tiling the one of the material the mesh uses
    (_used_material)."""
    found = []
    for kind, before, tag in _PLACES[field]:
        if field == 'tiling':  # one per material, Materials > Add's unused one too (REVIEW.md HLP-280)
            before = _IN_MATERIAL % re.escape(_used_material(content))
        pattern = r'(%s<%s>)\*?%s(</%s>)' % (before, tag, _KINDS[kind][0], tag)
        matches = list(re.finditer(pattern, content, re.S))
        if len(matches) != 1:
            raise RuntimeError(
                "the 3D view's state file holds the %s's <%s> %d times, not once: refused" % (field, tag, len(matches))
            )
        found.append(matches[0])
    return found


def _used_material(content: str) -> str:
    """The id of the material the state file's mesh uses, as the file holds it: the one its `material_mapping_table`
    maps each part of the mesh to. Raises unless it maps them all to one (MATERIALS_USED)."""
    table = re.search(r'<material_mapping_table>(.*?)</material_mapping_table>', content, re.S)
    found: list[str] = re.findall(
        r'<material_instance_id>([^<]*)</material_instance_id>', table.group(1) if table else ''
    )
    used = sorted(set(found))
    if len(used) != 1:
        named = ' (%s)' % ', '.join(html.unescape(u) for u in used) if used else ''
        raise RuntimeError(MATERIALS_USED % (len(used), named))
    return used[0]


def _state_fields(content: str, names: Sequence[StateField] = tuple(_PLACES)) -> StateFields:
    """The fields `names` of the state file `content`, every field the tools set by default. Raises when the file is
    of another format version than STATE_VERSION, or holds one of them other than once, or holds a camera that isn't
    level."""
    _state_version_checked(content)
    values = {name: [html.unescape(m.group(2)) for m in _located(content, name)] for name in names}
    fields = StateFields()
    if 'mesh' in values:
        fields['mesh'] = values['mesh'][0]
    if 'tiling' in values:
        fields['tiling'] = float(values['tiling'][0])
    if 'environment' in values:
        fields['environment'] = values['environment'][0]  # the scene's lighting map
    if 'rotation' in values:
        fields['rotation'] = float(values['rotation'][0])
    if 'exposure' in values:
        fields['exposure'] = float(values['exposure'][0])
    if 'camera' in values:
        matrix, distance = values['camera']
        fields['camera'] = _camera_pose([float(v) for v in matrix.split(',')], float(distance))
    return fields


def _float_text(value: float) -> str:
    """A number as Designer writes a float: 9 significant digits at most."""
    return '%.9g' % value


def _state_edited(content: str, fields: StateFields) -> str:
    """The state file `content` with `fields` written, the rest of it as it was. Raises, writing none of them, when
    the file is of another format version than STATE_VERSION, or holds one of them other than once."""
    _state_version_checked(content)
    texts: dict[StateField, list[str]] = {}  # each field's text, in each of its places
    if 'mesh' in fields:
        texts['mesh'] = [fields['mesh']]
    if 'tiling' in fields:
        texts['tiling'] = [_float_text(fields['tiling'])]
    if 'environment' in fields:
        texts['environment'] = [fields['environment']] * len(_PLACES['environment'])
    if 'rotation' in fields:
        texts['rotation'] = [_float_text(fields['rotation'])]
    if 'exposure' in fields:
        texts['exposure'] = [_float_text(fields['exposure'])]
    if 'camera' in fields:
        at = fields['camera']
        texts['camera'] = [','.join(_float_text(v) for v in _camera_matrix(at)), _float_text(at.distance)]
    spans = []  # (start, end, text): each value's text from after the element's start to its end, its * dropped
    for field, written in texts.items():
        places = zip(_PLACES[field], _located(content, field), written, strict=True)
        spans += [
            (m.end(1), m.start(3), _KINDS[kind][1] % html.escape(text, quote=False)) for (kind, _, _), m, text in places
        ]
    for start, end, text in sorted(spans, reverse=True):
        content = content[:start] + text + content[end:]
    return content


def _float32(value: float) -> float:
    """`value` as Designer holds a number of the state file: a 32-bit float (the module docstring)."""
    return float(struct.unpack('f', struct.pack('f', value))[0])


def _state_changes(held: StateFields, asked: StateFields) -> StateFields:
    """The fields of `asked`, but the camera, that `held` holds otherwise, as Designer holds them: a number as a 32-bit
    float (_float32)."""
    changes = StateFields()
    if 'mesh' in asked and asked['mesh'] != held['mesh']:
        changes['mesh'] = asked['mesh']
    if 'tiling' in asked and _float32(asked['tiling']) != _float32(held['tiling']):
        changes['tiling'] = asked['tiling']
    if 'environment' in asked and asked['environment'] != held['environment']:
        changes['environment'] = asked['environment']
    if 'rotation' in asked and _float32(asked['rotation']) != _float32(held['rotation']):
        changes['rotation'] = asked['rotation']
    if 'exposure' in asked and _float32(asked['exposure']) != _float32(held['exposure']):
        changes['exposure'] = asked['exposure']
    return changes


def _mesh_listed(content: str) -> bool:
    """Whether the Scene menu lists the mesh of the state file `content`. False for a mesh of the user's own
    (USERS_MESH). True for one of Designer's meshes, and for a file _state_fields refuses, such as one with no mesh id.
    It raises nothing (REVIEW.md HLP-287)."""
    try:
        return not _state_fields(content, ['mesh'])['mesh'].startswith(USERS_MESH)
    except RuntimeError:
        return True


def _state_text(path: str) -> str:
    """The state file `path`'s text, its line ends as they are."""
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def _state_write(path: str, content: str) -> None:
    """Writes `content` as the state file `path`, its line ends as given."""
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)


def _point_along(
    point: tuple[float, float, float], direction: Sequence[float], by: float
) -> tuple[float, float, float]:
    """`point` moved `by` along `direction`."""
    return (point[0] + by * direction[0], point[1] + by * direction[1], point[2] + by * direction[2])


def _camera_pose(matrix: Sequence[float], distance: float) -> Pose:
    """The camera's pose for its matrix and its distance, as the state file holds them: the point it looks at is its
    position less its distance along Z. Its yaw is X's angle, and its pitch is Z's against Y's, which turns past 90
    over the pole (Y pointing down). Raises for a camera whose X isn't level (CAMERA_LEVEL)."""
    x, y, z, position = matrix[0:3], matrix[4:7], matrix[8:11], matrix[12:15]
    if abs(x[1]) > CAMERA_LEVEL:  # REVIEW.md TST-902: a camera rolled about its own Z, which the decode can't give
        raise RuntimeError("the 3D view's state file holds a camera that isn't level: its X is %r" % list(x))
    target = _point_along((position[0], position[1], position[2]), z, -distance)
    return Pose(target, math.degrees(math.atan2(-x[2], x[0])), math.degrees(math.atan2(z[1], y[1])), distance)


def _camera_matrix(at: Pose) -> list[float]:
    """The camera's matrix for the pose `at`, as Designer writes it: X level with the ground, Y = Z x X."""
    yaw, pitch = math.radians(at.yaw), math.radians(at.pitch)
    z = [math.cos(pitch) * math.sin(yaw), math.sin(pitch), math.cos(pitch) * math.cos(yaw)]
    x = [math.cos(yaw), 0.0, -math.sin(yaw)]
    y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]]
    return [*x, 0.0, *y, 0.0, *z, 0.0, *_point_along(at.target, z, at.distance), 1.0]


def _camera_moved(
    start: Pose, viewport: tuple[float, float], orbit: tuple[float, float], pan: tuple[float, float], zoom: int
) -> Pose:
    """The pose `start` moved by an orbit, a pan and `zoom` steps closer (negative: away): `orbit` [right, up]
    degrees and `pan` [right, up] fractions of a `viewport` [width, height]. The orbit turns the camera sideways, the
    yaw the other way when it is upside down, then up. The pan then moves the point looked at along the turned
    camera's X and Y, its height's fraction in widths."""
    (width, height), (right, up), (across, rise) = viewport, orbit, pan
    # the turn sideways comes first, about the vertical; the camera upside down, the view's right is the other way
    sideways = right if math.cos(math.radians(start.pitch)) >= 0 else -right
    turned = Pose(start.target, start.yaw + sideways, start.pitch + up, start.distance)
    matrix = _camera_matrix(turned)
    step = PAN_RATE * start.distance
    target = _point_along(
        _point_along(start.target, matrix[0:3], step * across), matrix[4:7], step * rise * height / width
    )
    scale = ZOOM_STEP**zoom if zoom >= 0 else ZOOM_AWAY**-zoom
    return Pose(target, turned.yaw, turned.pitch, start.distance * scale)


def _framing(mesh: str, viewport: tuple[float, float]) -> tuple[tuple[float, float, float], float]:
    """Where Designer's Frame looks at the mesh of the state file's id `mesh`, in a `viewport` [width, height], from any
    direction: the point FRAMING gives, and its distance there, farther in a viewport wider than tall (FRAME_ANGLE). A
    mesh FRAMING lacks, such as a file of the user's own, is framed as the cube: the user's choice, 2026-11-25."""
    target, distance = next(
        ((target, distance) for mesh_id, target, distance in FRAMING.values() if mesh_id == mesh), FRAMING['Cube'][1:]
    )
    width, height = viewport
    return target, distance * math.sin(FRAME_ANGLE) / math.sin(FRAME_ANGLE / max(1.0, width / height))


def _framed(mesh: str, view: str, viewport: tuple[float, float]) -> Pose:
    """The pose Designer's Camera > `view` then Frame give the mesh of the state file's id `mesh`, in a `viewport`
    [width, height]: looking along the view's direction (VIEW_DIRECTIONS) as Frame does (_framing)."""
    target, distance = _framing(mesh, viewport)
    return Pose(target, *VIEW_DIRECTIONS[view], distance)


def _reframed(start: Pose, mesh: str, viewport: tuple[float, float]) -> Pose:
    """The pose `start` once the Scene menu switched to the mesh of the state file's id `mesh`, in a `viewport`
    [width, height]: its direction kept, looking as Frame does (_framing)."""
    target, distance = _framing(mesh, viewport)
    return start._replace(target=target, distance=distance)


def _state_default_path(folder: str) -> str:
    """The 3D view's default state file, for Designer's version folder `folder`: the user's Default State File when
    their project settings set one (`preferences/view3d/stateSaveFileUrl` in `user_project.sbsprj` there, a file URL),
    else STATE_NAME in the folder. A project file that can't be read sets none. Raises for a Default State File set
    otherwise than as a file URL: the file Designer saves then isn't known, and would be written with no backup.

    Designer reads the setting as it starts (measured 2026-11-25), and this reads it at each call: set in Project
    settings since Designer started, they may differ."""
    try:
        root = ElementTree.parse(os.path.join(folder, 'user_project.sbsprj')).getroot()
        url = (root.findtext('preferences/view3d/stateSaveFileUrl') or '').strip()
    except (OSError, ElementTree.ParseError):
        url = ''
    if not url:
        return os.path.join(folder, STATE_NAME)
    if not url.startswith('file://'):
        raise RuntimeError("the 3D view's Default State File %r isn't a file URL: refused" % url)
    return urllib.request.url2pathname(url[len('file://') :])  # file:///C:/... on Windows (REVIEW.md HLP-266)


def _state_resources(path: str) -> str:
    """The folder of the textures beside the state file `path`: its name, `_resources` in place of its extension."""
    return os.path.splitext(path)[0] + '_resources'


def _state_recorded(aside: str) -> str | None:
    """The path the backup `aside` came from (_state_back_up); None when it records none."""
    recorded = os.path.join(aside, 'path')
    return (_state_text(recorded) or None) if os.path.isfile(recorded) else None


def _state_removed(aside: str) -> None:
    """Removes the backup `aside`: renamed first, so a removal stopped midway leaves no backup."""
    removing = aside + '~'
    shutil.rmtree(removing, ignore_errors=True)
    os.rename(aside, removing)
    shutil.rmtree(removing)


def _state_back_up(path: str, aside: str) -> str | None:
    """Copies the state file `path` and its textures' folder, those of them there, into the new folder `aside`, with
    the path they came from. A backup left in `aside`, by a call that never put it back, is dealt with first, and the
    line to say returned (None when there was none):
    - put back where it came from (LEFTOVER_PUT_BACK);
    - removed when it can't be: it records no path, or the folder of its path is gone (LEFTOVER_REMOVED; the user,
      2026-11-26).
    The copy is made beside `aside`, then renamed to it, so a copy stopped midway is no backup."""
    path = os.path.abspath(path)  # what is recorded is what is copied (REVIEW.md HLP-263)
    leftover = None
    if os.path.isdir(aside):
        recorded = _state_recorded(aside)
        if recorded is not None and os.path.isdir(os.path.dirname(recorded)):
            _state_put_back(aside)
            leftover = LEFTOVER_PUT_BACK % recorded
        else:
            _state_removed(aside)
            why = (
                'the folder it came from is gone: %s' % os.path.dirname(recorded) if recorded else 'it records no path'
            )
            leftover = LEFTOVER_REMOVED % why
    making = aside + '~'  # a copy being made, or a backup being removed: never a backup
    shutil.rmtree(making, ignore_errors=True)
    os.makedirs(making)
    _state_write(os.path.join(making, 'path'), path)
    if os.path.isfile(path):
        shutil.copy2(path, os.path.join(making, 'file'))
    if os.path.isdir(_state_resources(path)):
        shutil.copytree(_state_resources(path), os.path.join(making, 'folder'))
    os.rename(making, aside)
    return leftover


def _state_put_back(aside: str) -> bool:
    """Makes the state file the backup `aside` came from (_state_back_up), and its textures' folder, what the backup
    holds, removing each one it lacks, then removes the backup. No other path is written or removed (REVIEW.md
    HLP-257). False, changing nothing, when there is no backup. Stopped midway, it leaves the backup, which the next
    put-back puts back again."""
    if not os.path.isdir(aside):
        return False
    path = _state_recorded(aside)
    if path is None:  # _state_back_up removes one so
        raise RuntimeError("the 3D view's state backup %s records no path: not put back" % aside)
    folder = _state_resources(path)
    if os.path.isfile(path):
        os.remove(path)
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    if os.path.isfile(os.path.join(aside, 'file')):
        shutil.copy2(os.path.join(aside, 'file'), path)
    if os.path.isdir(os.path.join(aside, 'folder')):
        shutil.copytree(os.path.join(aside, 'folder'), folder)
    _state_removed(aside)
    return True
