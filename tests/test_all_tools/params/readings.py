"""How params' checks of a Gradient Map's keys and a Curve's points (checks.py) read what Designer gives back: the
facts script's ramps (designer_scripts/keys.py) as it prints them, the prepared ramp's bands (preparations.py) as
node_stats samples them, and a parameter as describe_graph lists it."""

import ast
import json
import re

from test_all_tools.common import Ctx, Json, pixel_values, text

CURVES = ('curveluminance', 'curvered', 'curvegreen', 'curveblue', 'curvealpha')  # a Curve's arrays of points
# keys.py's ramp at its pixels 0, 3, 5, 7, 10, 12 and 15, which read i/15, and each turned into 1 - x
RAMP = ('0.000', '0.200', '0.333', '0.467', '0.667', '0.800', '1.000')
RAMP_INVERTED = ('1.000', '0.800', '0.667', '0.533', '0.333', '0.200', '0.000')
GREY_RAMP, GREY_INVERTED = 'LUM32F ' + ' '.join(RAMP), 'LUM32F ' + ' '.join(RAMP_INVERTED)
RED_TO_BLUE = 'RGBA32F ' + ' '.join('%s/0.000/%s/1.000' % (RAMP_INVERTED[i], RAMP[i]) for i in range(7))
ALL_RED = 'RGBA32F ' + ' '.join(['1.000/0.000/0.000/1.000'] * 7)


def colour_ramp(*inverted: int) -> str:
    """keys.py's colour ramp, (x, x, x, x), with the channels `inverted` (0 for R up to 3 for A) turned into 1 - x."""
    return 'RGBA32F ' + ' '.join(
        '/'.join((RAMP_INVERTED if channel in inverted else RAMP)[i] for channel in range(4)) for i in range(7)
    )


BANDS = (0.0, 0.25, 0.5, 0.75, 1.0)  # what the prepared ramp reads, band by band from the left


async def band_values(ctx: Ctx, node: str) -> tuple[str, list[list[float]]]:
    """node_stats of `node` at a pixel in the middle of each of the ramp's five bands, on row 10 of the 512 px graph:
    its text, and each band's values in order."""
    points = [[int((band + 0.5) * 512 / 5), 10] for band in range(5)]
    t = text(await ctx.c('node_stats', {'node_id': node, 'points': points, **ctx.G}))
    return t, list(pixel_values(t).values())


def read_back(described: str, pid: str) -> str:
    """What describe_graph(include_params) says a parameter is: the text after `<pid> = `, or '' when not listed."""
    found = re.search(r'^\s+%s = (.*)$' % re.escape(pid), described, re.M)
    return found.group(1) if found else ''


def as_json(shown: str) -> Json:
    """A value describe_graph or set's result shows, such as keys, as JSON gives it back to set: its tuples as lists;
    None for '', a value not listed."""
    again: Json = json.loads(json.dumps(ast.literal_eval(shown))) if shown else None
    return again
