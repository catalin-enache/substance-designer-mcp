"""The 3D view's own state file (`.sbsscn`, ROADMAP item 131): the fields the tools set, read and edited in its text,
the rest of it kept byte for byte; the fields said under the names of screenshot_designer's options where one sets
them, for the 3D view as text (_state_said, ROADMAP item 85); the camera's pose and its moves; and the backup of the
file and its textures' folder, put back; the pose of a view, framed as Designer's Frame does; the default state file's
path. The caller gives
the folders. The part takes only the standard library's names from core, so the tests run it as a module of its own
(designer_helpers.standalone), and facts' state file checks check Designer against this code
(tests/test_all_tools/facts/state_file.py and state_camera.py). scene3d.py drives the file in Designer.

What it relies on, measured on macOS in Designers an agent started (Designer 16.0.7, 2026-11-25), and pinned by those
checks, but for the moves (below):

- The format is version 10 (STATE_VERSION). Each field the tools set (StateField), edited alone, loads alone, and all
  of them edited load in one Reset Scene:
  - `mesh`: the mesh's id in `external_scenes` (`sphere`), or a mesh file of the user's own as USERS_MESH and its
    absolute path (_mesh_id). Designer reads the id as a URL: a `#`, `?` or `%XX` written as it is made a fragment, a
    query or an escape, and the file didn't import. Encoded as %23, %3F and %25, as Designer saves a mesh dropped on the
    view, they imported. `"`, `<`, `>`, `^`, a backtick, `{`, `|`, `}`, `[`, `]` and a backslash imported as written,
    but were saved encoded, as Qt's QUrl.fromLocalFile gives them. A space, `é`, `&`, `'`, `+`, `;`, `=`, `@`, `$`,
    `!`, `(`, `)`, `*`, `~`, `,` and `:` imported as written, and were saved back so (REVIEW.md HLP-300, HLP-308,
    HLP-310). `#`, `|` and a space are checked live (facts' check of a mesh file framed by Frame); the others were
    measured by runners' probes (2026-11-27), not checked. A load of another mesh's id keeps the file's camera:
    Designer doesn't frame the new mesh;
  - `tiling`: the `___usd___tiling` of the material the mesh uses. Each material holds one, a material Materials > Add
    added too, which `material_mapping_table` maps no part of the mesh to (_used_material). A mesh of the Scene menu's
    uses Default (DEFAULT_MATERIAL), whatever else the table holds: the Plane loaded over the project's OBJ's state
    mapped to Default, the OBJ's two entries left in the table (2026-11-27, facts' check of a Scene menu's mesh shot
    over a mesh file's view; REVIEW.md HLP-311). A load with Default's tiling edited tiles it, a material Materials >
    Add added beside it (editor_panels_and_fit's check of an unused material). A mesh file uses the one the table maps
    each part to, of those the Materials menu lists in use (view3d.py). A mesh file loaded over another mesh file's view
    kept the earlier file's entries in the table beside its own, its entries naming no mesh: the project's OBJ and one
    of one material, each over the other (a probe, 2026-11-28; REVIEW.md HLP-322). Facts' check of a tiling on a mesh
    file over another's view checks that the tiling then goes in the new file's material, and that the refusal names the
    new file's materials alone;
  - `environment`: the environment's map, as a URL. Each of Designer's own maps is MAP_SCHEME and its file's name, as
    a drop of each of the 34 saved it (`sd-3dview-maps://studio 02.exr`, its space kept), and Save copies no map
    beside the file. Four places hold it, and an edit writes all four: the scene's textures, the lighting's and the
    background's, and the Environment entity's own two;
  - `rotation`: the environment's, the entity's `dome/rotation_angle`, in turns about Y: 0.25 shows as 90 degrees
    in Environment > Edit properties;
  - `exposure`: the entity's `intensity`, which that panel shows as the Exposure;
  - `camera`: the Default Camera entity's `local_transform` and `dist_to_target`;
  - `shader`: the shader model of the material the mesh uses, the `<definition>`'s `<name>` in that material's entry
    of the renderer plugin's materials list (`HdEclairRendererPlugin`), found by the material's id (_used_material).
    Each of the Materials menu's models picked was saved so (SHADER_MODELS, 2026-11-27). A load with the name alone
    edited set the model of the session's Default, held overridden (facts' check of one field edited); scene3d.py says
    when a load didn't.
- A value set is written with no `*` in front, so an edit drops the `*` that marks a value at Designer's default.
- Designer holds the tiling, the rotation and the exposure as 32-bit floats, and saves each to 9 significant digits:
  a tiling of 2.3 written is saved 2.29999995 (_float32). The 3D view as text says each with the fewest decimals
  that give that float back (_said_float): 2.3.
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
  (_state_resources); with no graph's outputs there, no folder. Each material showing them names a texture there in its
  parameters (_materials_linked), on the project's OBJ with the outputs on `first` alone and on both (facts' check of
  graph= on mesh files); a probe saw each name its own (`first_baseColor.png`). A material's
  `override_existing_material` doesn't tell it, as a probe measured (2026-11-27): false for `first` once its Override
  Material was turned off, its textures still named, and true for Default with no outputs, the Plane loaded over the
  OBJ's state.
- The default state file is STATE_NAME in Designer's version folder, or the user's Default State File, a file URL in
  their project settings (_state_default_path). Designer reads that setting as it starts (2026-11-26, the self-test's
  lifecycle check).
- A view's pose (_framed), measured 2026-11-26 in Designers an agent started, with Designer's default lens:
  - Camera > <view> looks along the view's direction (VIEW_DIRECTIONS). Frame then looks at a point of the mesh's own
    from a distance of its own (FRAMING, _framing), whatever the view: on each of the 11 meshes, Front, Top and Default
    gave one point and distance. A mesh picked in the Scene menu is framed the same way, the camera's direction kept,
    which mesh= does through the file;
  - the distance is FRAMING's x sin(FRAME_ANGLE) / sin(FRAME_ANGLE x the viewport's height over its width), never
    less than FRAMING's, a sine below 0 included, measured up to 3.87 times as tall as wide. FRAME_ANGLE is
    2 atan(18 / 35), the default 35 mm lens across a 36 mm frame. It fitted 17 viewports from 1.07 to 3.89 times as wide as tall within 2e-7 of the distance
    (2026-11-26), and 18 taller than wide to 3 decimals (a runner's probe, 2026-11-27, not checked; REVIEW.md TST-992,
    HLP-306): farther by 1.0 to 14.7 times from about 0.30 to 0.44 times as wide as tall (161 x 423 by 1.352, 161 x 523
    by 14.664), FRAMING's elsewhere (161 x 573, 186 x 423 and up). The live check frames each mesh in one viewport taller
    than wide and one wider than tall;
  - a fresh Designer's own mesh has another id than the Scene menu's Rounded cube (`Rounded Cube`): framed as the
    cube, whose point is the same and whose distance is within 2e-7;
  - a mesh file of the user's own isn't in FRAMING: Designer's own Frame frames it (scene3d.py).
- A backup an earlier call left is put back first, or removed when it records no path or its path's folder is gone
  (_state_back_up; the user, 2026-11-26).

Measured, not checked:
- a load with the used material's tiling edited left the unused one's as it was, and a mesh of another id loaded with
  it was mapped to the same material, the default one (once each, 2026-11-26);
- a value at Designer's default is written with a `*` in front (`*float(1)`, the unit tests' fixture);
- each of the map's four places set the map in a Designer just started. Once a map had been dropped on the view, the
  entity's own two alone didn't (one Designer each);
- a file saved with the GPU Pathtracer set holds each place once, as the Rasterizer's does (once, 2026-11-25), the
  shader's too (a runner's probe, 2026-11-27);
- a load of the shader model's name alone changed that material's parameters with it, in its entry of the renderer
  plugin's list and in the file's own materials list (`/database/materials/materials`). Each load was made onto the
  state the one before left: 118 paths from OpenPBR Surface to AdobeStandardMaterial, 55 from there to
  UsdPreviewSurface, and 66 from there back to OpenPBR Surface (once each, 2026-11-27).

Not measured:
- a turn sideways from the poles, Top and Bottom, where the yaw's direction would follow a cosine of float noise
  (_camera_moved);
- a turn sideways from below the south pole, a pitch under -90, where _camera_moved turns the yaw the other way, as
  over the north pole;
- a turn up from a camera upside down;
- a render under each shader model with the GPU Pathtracer (shot3d.py records the Rasterizer's).
"""

import shutil
import struct
import urllib.request

from .core import ElementTree, Literal, NamedTuple, Sequence, TypedDict, assert_never, html, math, os, re

STATE_VERSION = '10'  # the format's version, its settingsInfo
STATE_NAME = 'user_view3d_settings.sbsscn'  # the default state file, in Designer's version folder
STATE_BACKUP = 'sd_mcp_3d_view_backup'  # the 3D shot's backup of it, a folder in Designer's version folder
PAN_RATE = 1.021  # x the distance: how far a pan of a view's width moves the point looked at
ZOOM_STEP = 0.9  # x the distance, a step closer
ZOOM_AWAY = 1.1  # x the distance, a step away: not 1 / ZOOM_STEP
CAMERA_LEVEL = 1e-4  # X's y at most, a camera level: Designer's saved 0, or -0 (2026-11-25)
DEGREES_PER_TURN = 360.0  # the environment's rotation: in turns in the file, in degrees in the tool
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
# distance there, as Designer saved them (2026-11-26) in a viewport taller than wide, which _framing scales by the
# viewport's aspect
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
# radians: Frame's distance is FRAMING's x sin(FRAME_ANGLE) / sin(FRAME_ANGLE x the viewport's height over its width),
# never less than FRAMING's. It is the default 35 mm lens's angle across a 36 mm frame (the module docstring)
FRAME_ANGLE = 2 * math.atan(18 / 35)
MAP_SCHEME = 'sd-3dview-maps://'  # the file names one of Designer's environment maps by it, then the map's file's name
# the file names a mesh of the user's own, which the Scene menu doesn't list, by its file's URL: this and its absolute
# path, encoded as _mesh_id encodes it
USERS_MESH = 'file://'
# the characters a mesh file's URL holds encoded, as Designer saves it: QUrl.fromLocalFile's (REVIEW.md HLP-300,
# HLP-308, HLP-310)
URL_ESCAPES = str.maketrans({c: '%%%02X' % ord(c) for c in '%#?"<>^`{|}[]\\'})
# each shader model of a material's submenu in the 3D view's Materials menu, in its order: the name of its definition in
# the state file, as Designer saved it picked there (2026-11-27)
SHADER_MODELS: dict[str, str] = {
    'AdobeStandardMaterial': 'usd::AdobeStandardMaterial_4_0',
    'OpenPBR Surface': 'usd::ND_open_pbr_surface_surfaceshader',
    'UsdPreviewSurface': 'usd::UsdPreviewSurface',
}
# the mesh using other than one material, then their names in brackets: tiling= or shader_model= would set one of them
# (REVIEW.md TST-315). The Materials menu (view3d._material_checked) and the state file (_used_material) tell them
MATERIALS_USED = "the 3D view's mesh uses %d materials%s: tiling= and shader_model= set the material of a mesh with one"
LEFTOVER_PUT_BACK = "a backup of the 3D view's default state, left by an earlier call, was put back first: %s"
LEFTOVER_REMOVED = (
    "a backup of the 3D view's default state, left by an earlier call, couldn't be put back (%s), and was removed"
)

StateField = Literal['mesh', 'tiling', 'environment', 'rotation', 'exposure', 'camera', 'shader']  # of StateFields
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
    shader: str  # the shader model of the material the mesh uses, the name of its definition (SHADER_MODELS)


# What comes before a value's element, inside the element named: `.` takes newlines too, and `(?:(?!</x>).)*?` stays
# inside x, so a value missing there isn't taken from an element after it
_IN_MESH = r'<external_scenes>(?:(?!</external_scenes>).)*?'  # the first scene's: the files measured held one
_IN_SCENE_TEXTURES = r'<scene_textures>(?:(?!</scene_textures>).)*?'
_IN_ENVIRONMENT = r'<name>Environment</name>(?:(?!</components>).)*?'
_IN_CAMERA = r'<name>Default Camera</name>(?:(?!</components>).)*?'
# the materials list's entry of the material of id %s, as the file holds it, escaped as a regex; the mapping table's
# entries follow its id with no <material>
_IN_MATERIAL = r'<material_instance_id>%s</material_instance_id>\s*<material>(?:(?!</material>).)*?'
# the renderer plugin's entry of the material of id %s, as _IN_MATERIAL takes it: its definition, after the entry's id
_IN_DEFINITION = r'<HdEclairRendererPlugin>(?:(?!</HdEclairRendererPlugin>).)*?<id>%s</id>\s*<definition>\s*'
# Each kind of value: the regex of its text, its group the value's text, and the text written for a value's text. A
# value's text is unescaped once read and escaped to be written, as XML holds text
_KINDS: dict[_ValueKind, tuple[str, str]] = {
    'float': (r'float\(([^)]*)\)', 'float(%s)'),
    'text': (r'([^<]*)', '%s'),
    'map': (r'\[\(loaderType\)\(file\)\]\[\(file\)\((.*?)\)\]', '[(loaderType)(file)][(file)(%s)]'),
    'matrix': (r'list&lt;float&gt;\[16\]\(([^)]*)\)', 'list&lt;float&gt;[16](%s)'),
}
# Each field's places, every field the tools set: its kind there, what comes before the element, and the element's tag.
# What comes before the element of a field of the material the mesh uses (PER_MATERIAL) takes that material's id
_PLACES: dict[StateField, tuple[tuple[_ValueKind, str, str], ...]] = {
    'mesh': (('text', _IN_MESH, 'id'),),
    'tiling': (('float', _IN_MATERIAL, '___usd___tiling'),),
    'environment': (
        ('map', _IN_SCENE_TEXTURES, 'environment'),
        ('map', _IN_SCENE_TEXTURES, 'panorama'),
        ('map', _IN_ENVIRONMENT, 'environment_texture'),
        ('map', _IN_ENVIRONMENT, 'panorama_texture'),
    ),
    'rotation': (('float', _IN_ENVIRONMENT, 'rotation_angle'),),
    'exposure': (('float', _IN_ENVIRONMENT, 'intensity'),),
    'camera': (('matrix', _IN_CAMERA, 'local_transform'), ('float', _IN_CAMERA, 'dist_to_target')),
    'shader': (('text', _IN_DEFINITION, 'name'),),
}
# the fields of the material the mesh uses: one per material, Materials > Add's unused one too (REVIEW.md HLP-280)
PER_MATERIAL: tuple[StateField, ...] = ('tiling', 'shader')
DEFAULT_MATERIAL = 'default'  # the id of Default, the material a mesh of the Scene menu's uses (_used_material)


def _state_version_checked(content: str) -> None:
    """Raises unless the state file `content` is of the format version STATE_VERSION."""
    found = re.search(r'<settingsInfo>\s*<version>([^<]*)</version>', content)
    version = found.group(1).strip() if found else None
    if version != STATE_VERSION:
        raise RuntimeError(
            "the 3D view's state file is of format version %s, and only version %s is known: refused"
            % (version or 'none', STATE_VERSION)
        )


def _located(content: str, field: StateField, in_use: Sequence[str] = ()) -> list[re.Match[str]]:
    """Each place of `field` in the state file `content`, its match's groups the text before the value, the value and
    the text after (a `*` before the value outside them). Raises unless the file holds each place once, as found from
    its anchor: the mesh's id is the first in `external_scenes`, and the tiling and the shader model those of the
    material the mesh uses (PER_MATERIAL, _used_material, which takes `in_use`)."""
    found = []
    for kind, before, tag in _PLACES[field]:
        if field in PER_MATERIAL:
            before = before % re.escape(_used_material(content, in_use))
        pattern = r'(%s<%s>)\*?%s(</%s>)' % (before, tag, _KINDS[kind][0], tag)
        matches = list(re.finditer(pattern, content, re.S))
        if len(matches) != 1:
            raise RuntimeError(
                "the 3D view's state file holds the %s's <%s> %d times, not once: refused" % (field, tag, len(matches))
            )
        found.append(matches[0])
    return found


def _used_material(content: str, in_use: Sequence[str] = ()) -> str:
    """The id of the material the state file's mesh uses, as the file holds it. A mesh of the Scene menu's
    (_mesh_listed) uses its own, DEFAULT_MATERIAL, whatever else the `material_mapping_table` holds: a mesh file's
    entries are left there (the module docstring; REVIEW.md HLP-311). A mesh file of the user's own (USERS_MESH) uses
    the one its table maps each part to. With `in_use`, the names of the materials the Materials menu lists in use, it
    is one of those: the table also keeps the entries of a mesh file loaded before (the module docstring; REVIEW.md
    HLP-322). The names are compared with their `&` dropped, as the menu drops it (view3d._materials_used; REVIEW.md
    HLP-323, HLP-325); with none named so, every one counts. Raises unless they come to one (MATERIALS_USED)."""
    if _mesh_listed(content):
        return DEFAULT_MATERIAL
    table = re.search(r'<material_mapping_table>(.*?)</material_mapping_table>', content, re.S)
    found: list[str] = re.findall(
        r'<material_instance_id>([^<]*)</material_instance_id>', table.group(1) if table else ''
    )
    ids = sorted(set(found))
    used = [u for u in ids if _material_named(content, u).replace('&', '') in in_use] or ids
    if len(used) != 1:
        named = ' (%s)' % ', '.join(html.unescape(u) for u in used) if used else ''
        raise RuntimeError(MATERIALS_USED % (len(used), named))
    return used[0]


def _materials_linked(content: str, folder: str) -> list[str]:
    """The names of the materials of the state file `content` that showed a graph's outputs as it was saved, in the
    file's order: those whose parameters name a texture in the textures' folder `folder` beside it (_state_resources).
    A Save names a texture of each such material there, also with its Override Material off (the module docstring)."""
    inside = r'\(file\)\([^)]*[/\\]%s[/\\]' % re.escape(os.path.basename(folder))
    linked = []
    for m in re.finditer(_IN_MATERIAL % r'[^<]*' + '</material>', content, re.S):  # each material's entry
        name = _material_name(m.group(0)) if re.search(inside, m.group(0)) else None
        linked += [name] if name is not None else []
    return linked


def _material_name(entry: str) -> str | None:
    """The name of the material whose entry of the state file's materials list is `entry`; None when it holds none."""
    name = re.search(r'</parameters>(?:(?!</material>).)*?<name>([^<]*)</name>', entry, re.S)
    return html.unescape(name.group(1)) if name is not None else None


def _material_named(content: str, material: str) -> str:
    """The name of the material of id `material` in the state file `content`: its entry's in the materials list, else
    its id."""
    entry = re.search(_IN_MATERIAL % re.escape(material) + '</material>', content, re.S)
    return (_material_name(entry.group(0)) if entry is not None else None) or html.unescape(material)


def _state_overridden(content: str, in_use: Sequence[str] = ()) -> tuple[str, str | None]:
    """The state file `content` with the material the mesh uses (_used_material, which takes `in_use`) held overridden,
    its `override_existing_material` true, and that material's name when the file held it not overridden, else None. A
    load set Default's model only so, and the render showed a model or a tiling only with Override on (scene3d.py;
    REVIEW.md HLP-316, HLP-321). Raises when the file holds that material's Override Material other than once."""
    used = _used_material(content, in_use)
    pattern = (
        _IN_MATERIAL % re.escape(used) + '<override_existing_material>(true|false)<(?:(?!</material>).)*</material>'
    )
    found = list(re.finditer(pattern, content, re.S))
    if len(found) != 1:
        raise RuntimeError(
            "the 3D view's state file holds the Override Material of the material the mesh uses %d times, not once: "
            'refused' % len(found)
        )
    m = found[0]
    if m.group(1) == 'true':
        return content, None
    return content[: m.start(1)] + 'true' + content[m.end(1) :], _material_named(content, used)


def _state_fields(
    content: str, names: Sequence[StateField] = tuple(_PLACES), in_use: Sequence[str] = ()
) -> StateFields:
    """The fields `names` of the state file `content`, every field the tools set by default, the material's found as
    _used_material finds it from `in_use`. Raises when the file is of another format version than STATE_VERSION, or
    holds one of them other than once, or holds a camera that isn't level."""
    _state_version_checked(content)
    values = {name: [html.unescape(m.group(2)) for m in _located(content, name, in_use)] for name in names}
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
    if 'shader' in values:
        fields['shader'] = values['shader'][0]
    return fields


def _float_text(value: float) -> str:
    """A number as Designer writes a float: 9 significant digits at most."""
    return '%.9g' % value


def _state_edited(content: str, fields: StateFields, in_use: Sequence[str] = ()) -> str:
    """The state file `content` with `fields` written, the rest of it as it was. The tiling and the shader model are
    written in the material the mesh written uses (_used_material, which takes `in_use`; REVIEW.md HLP-311). Raises,
    writing none of them, when the file is of another format version than STATE_VERSION, or holds one of them other than
    once."""
    _state_version_checked(content)
    texts: dict[StateField, list[str]] = {}  # each field's text, in each of its places, the mesh's first
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
    if 'shader' in fields:
        texts['shader'] = [fields['shader']]
    for field, written in texts.items():  # each field found in the file as the ones before left it
        places = zip(_PLACES[field], _located(content, field, in_use), written, strict=True)
        # (start, end, text): each value's text from after the element's start to its end, its * dropped
        spans = [
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
    if 'shader' in asked and asked['shader'] != held['shader']:
        changes['shader'] = asked['shader']
    return changes


def _said_float(held: float, scale: float = 1.0) -> str:
    """The state file's number `held` times `scale`, in the tool's units, with the fewest decimals that give back the
    32-bit float Designer holds (_float32) once divided by `scale`, never in exponent form (90, not 9e+01). Given back
    to an option that takes it, the value is the one shown already (_state_changes)."""
    value, kept = held * scale + 0.0, _float32(held)  # -0 said as 0
    for decimals in range(17):
        said = '%.*f' % (decimals, value)
        if _float32(float(said) / scale) == kept:
            return said
    return repr(value)


def _mesh_id(mesh: str) -> str:
    """The id the state file holds `mesh` by: one of the Scene menu's by its id (FRAMING), else a mesh file's absolute
    path by its URL (USERS_MESH), the characters of URL_ESCAPES encoded (%25 for %), as Designer saves a mesh
    dropped on the view (QUrl.fromLocalFile). Its other characters stay as written. _mesh_said says the id back as
    `mesh`."""
    return FRAMING[mesh][0] if mesh in FRAMING else USERS_MESH + mesh.translate(URL_ESCAPES)


def _mesh_said(mesh: str) -> str:
    """The state file's mesh `mesh` said: one of the Scene menu's by its name there (FRAMING), one of the user's own by
    its file's path (USERS_MESH), else its id as the file holds it."""
    if mesh.startswith(USERS_MESH):
        return urllib.request.url2pathname(mesh[len(USERS_MESH) :])
    return next((name for name, (mesh_id, _, _) in FRAMING.items() if mesh_id == mesh), mesh)


def _map_said(url: str) -> str:
    """The environment's map `url` as environment= takes it: one of Designer's own by its file's name without its
    extension (MAP_SCHEME), else the URL as the file holds it."""
    return os.path.splitext(url[len(MAP_SCHEME) :])[0] if url.startswith(MAP_SCHEME) else url


def _shader_said(definition: str) -> str:
    """The shader model of the state file's definition name `definition` as shader_model= takes it, its name in the
    Materials menu (SHADER_MODELS); else the name as the file holds it."""
    return next((name for name, held in SHADER_MODELS.items() if held == definition), definition)


def _rounded(value: float) -> str:
    """A camera's angle or length said to 2 decimals, -0 as 0."""
    return '%g' % (round(value, 2) + 0.0)


def _pose_said(at: Pose) -> str:
    """The camera's pose `at` said: its yaw and pitch, the point it looks at and its distance. While its pitch is
    within 90 degrees, it also names the options that turn a framed camera so: view Front, then orbit [yaw, pitch]
    (VIEW_DIRECTIONS, _camera_moved)."""
    yaw, pitch = _rounded(at.yaw), _rounded(at.pitch)
    if abs(at.pitch) <= 90:
        turned = 'view Front then orbit [%s, %s]' % (yaw, pitch)
    else:
        turned = 'over the pole: no view and orbit give it'
    looking = ', '.join(_rounded(v) for v in at.target)
    return 'yaw %s, pitch %s degrees (%s), looking at (%s) from %s away' % (
        yaw,
        pitch,
        turned,
        looking,
        _rounded(at.distance),
    )


# each field said under the name of the screenshot_designer option that sets it, where that isn't the field's own
SAID_AS: dict[StateField, str] = {
    'rotation': 'environment_rotation',
    'exposure': 'environment_exposure',
    'shader': 'shader_model',
}


def _field_said(fields: StateFields, name: StateField, mesh: str | None) -> str:
    """The field `name` of `fields` said, in the tool's units (_state_said)."""
    if name == 'mesh':
        return mesh if mesh is not None else _mesh_said(fields['mesh'])
    if name == 'environment':
        return _map_said(fields['environment'])
    if name == 'rotation':
        return _said_float(fields['rotation'], DEGREES_PER_TURN)
    if name == 'camera':
        return _pose_said(fields['camera'])
    if name == 'tiling':
        return _said_float(fields['tiling'])
    if name == 'exposure':
        return _said_float(fields['exposure'])
    if name == 'shader':
        return _shader_said(fields['shader'])
    assert_never(name)  # a field with no branch here: the checker names it


def _state_said(content: str, mesh: str | None, in_use: Sequence[str] = ()) -> list[str]:
    """What the state file `content` holds of the 3D view, a line each in _PLACES' order. Each line is `<option>:
    <value>`, under the name of the screenshot_designer option that sets the field (SAID_AS) and in its units: a value
    that option takes, given back to it, reads as shown already, but a tiling or a shader model on a material whose
    Override Material is off, which the set-up turns on (scene3d.py, step 4). A map not of Designer's own is said by its
    URL instead (_map_said), a shader model the Materials menu lacks by its name in the file, which shader_model=
    refuses (_shader_said), and the camera by _pose_said. `mesh` is the Scene menu's entry the view checks, which names
    the mesh; None when it checks none, and the file's mesh is said. `in_use`: as _used_material takes it. A field the
    file holds other than once is said not read, with why, and so are the tiling and the shader model of a mesh using
    several materials. Raises for a file of another format version than STATE_VERSION."""
    _state_version_checked(content)
    said = []
    for name in _PLACES:
        try:
            value = _field_said(_state_fields(content, [name], in_use), name, mesh)
        except RuntimeError as e:
            value = 'not read: %s' % e
        said.append('%s: %s' % (SAID_AS.get(name, name), value))
    return said


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
    direction: the point FRAMING gives, and its distance there, farther in a viewport wider than tall, and in one about
    0.30 to 0.44 times as wide as tall (FRAME_ANGLE; REVIEW.md HLP-306). A mesh FRAMING lacks, such as a fresh
    Designer's own Rounded Cube, is framed as the cube: the user's choice, 2026-11-25. The set-up has Designer's Frame
    frame a mesh file of the user's own instead (scene3d.py)."""
    target, distance = next(
        ((target, distance) for mesh_id, target, distance in FRAMING.values() if mesh_id == mesh), FRAMING['Cube'][1:]
    )
    width, height = viewport
    # from 180 degrees, where the sine is below 0, max keeps FRAMING's (measured to 210: 161 x 623)
    return target, distance * max(1.0, math.sin(FRAME_ANGLE) / math.sin(FRAME_ANGLE * height / width))


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
