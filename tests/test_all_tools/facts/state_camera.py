"""The 3D view's camera as its state file holds it (state_file.py), for facts' state file checks: the poses they put
in a state file and compare. The decode of the camera to a pose and back, the set-up's moves (ROADMAP item 74) and a
view's framing are designer_helpers/state3d.py's own, which these checks run.

Measured on macOS in Designers an agent started (Designer 16.0.7), and checked:
- each view framed on the Plane, in the self-test's viewport, looks along its own direction at Frame's point and
  distance, and each mesh is framed at its point and distance in a viewport taller than wide and in one wider than
  tall, as state3d's VIEW_DIRECTIONS, FRAMING and FRAME_ANGLE give them (2026-11-26).

Measured on 2026-11-25 against the drags of the set-up then, not checked here since the drags went (2026-11-26): the
camera's decode, and the orbit, pan and zoom, as state3d.py's docstring gives them (PAN_RATE, ZOOM_STEP and ZOOM_AWAY
included), over the pole too. The editor_panels_and_fit checks of the moves check what they do against Designer's own
views and the plane's movement, each to the precision state3d.py's docstring gives (REVIEW.md TST-919).
"""

from typing import TYPE_CHECKING

import designer_helpers

if TYPE_CHECKING:  # for the checker: the part as the helpers hold it
    from designer_helpers import state3d
else:
    state3d = designer_helpers.standalone('state3d')

# the one-field check's camera: AWAY, (yaw, pitch), where its base is put, then GLIDES_TO, where its camera's row
# turns it, a load gliding the camera from one to the other (state_file.py; a pose at yaw 180 was jumped to instead)
AWAY = (90.0, 20.0)
GLIDES_TO = (135.0, 10.0)
UNFRAMED = (10.0, 5.0, -20.0)  # a point Frame looks at on no mesh (state3d.FRAMING): a camera put there isn't framed


def pose(content: str) -> state3d.Pose:
    """The camera's pose in the state file `content`, as state3d.py reads it; raises unless it has one camera."""
    return state3d._state_fields(content, ['camera'])['camera']


def away(content: str) -> str:
    """The state file `content` with its camera at AWAY, looking at the same point from as far; raises unless it has
    one camera."""
    before = pose(content)
    return state3d._state_edited(content, {'camera': state3d.Pose(before.target, *AWAY, before.distance)})


def turned(content: str) -> str:
    """The state file `content` with its camera at GLIDES_TO and a quarter further away, looking at the same point;
    raises unless it has one camera."""
    before = pose(content)
    return state3d._state_edited(content, {'camera': state3d.Pose(before.target, *GLIDES_TO, before.distance * 1.25)})


def angle_off(a: float, b: float) -> float:
    """How far apart two angles in degrees are, across the turn."""
    return abs((a - b + 180) % 360 - 180)


def turned_apart(a: state3d.Pose, b: state3d.Pose) -> float:
    """How far two poses are turned apart: the degrees of their yaws apart and of their pitches."""
    return angle_off(a.yaw, b.yaw) + angle_off(a.pitch, b.pitch)


def alike(a: state3d.Pose, b: state3d.Pose) -> bool:
    """Two poses one, as Designer saves them: within 0.01 degrees, and 1e-4 of the distance."""
    near = 1e-4 * max(a.distance, b.distance)
    return (
        turned_apart(a, b) < 0.01
        and abs(a.distance - b.distance) <= near
        and all(abs(x - y) <= near for x, y in zip(a.target, b.target, strict=True))
    )


def said(at: state3d.Pose) -> str:
    """A pose, said in a check's detail."""
    return 'yaw %.2f pitch %.2f at (%.2f, %.2f, %.2f) from %.3f' % (at.yaw, at.pitch, *at.target, at.distance)
