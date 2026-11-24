"""Bitmaps: apply_edits' bitmap op, compare_to_reference and analyze_reference; the greys Designer's nodes make of a
colour image, and a photo's palette on a Gradient Map, end to end (ROADMAP items 116 and 119)."""

import json
import os
import re
from typing import Literal

import numpy as np
from PIL.Image import Transpose

from test_all_tools.bitmaps.palettes import (
    RAMP,
    STRIP,
    expected_greys,
    palette,
    photo,
    rgb_rmse,
    strip,
    strip_points,
)
from test_all_tools.common import CLOSE, Ctx, JsonSent, ToolArgs, added_id, check, near, pixel_values, refs, text


async def run(ctx: Ctx) -> None:
    await check_analyze_reference(ctx)
    await check_designer_greys(ctx)
    await check_photo_to_gradient_map(ctx)
    await check_a_bitmap_computes_at_sides_of_powers_of_2(ctx)
    await check_a_bitmap_turns_a_jpeg_by_its_orientation_and_no_other_format(ctx)
    c, scratch, G = ctx.c, ctx.scratch, ctx.G
    # --- bitmaps
    from PIL import Image

    png = os.path.join(scratch, 'selftest_bitmap.png')
    Image.new('RGB', (64, 32), (200, 100, 50)).save(png)
    t = text(await c('apply_edits', {'ops': [{'op': 'bitmap', 'path': png, 'position': [-600, 300]}], **G}))
    check('apply_edits', 'bitmap: linked, native size', 'size (6, 5)' in t, t)
    bm = added_id(t)
    t = text(await c('node_stats', {'node_id': bm, 'points': [[0, 0]], **G}))
    check('apply_edits', 'bitmap: pixels match file', 'R=0.7843, G=0.3922, B=0.1961' in t, t)
    t = text(
        await c(
            'apply_edits', {'ops': [{'op': 'bitmap', 'path': png, 'ref': 'img'}, {'op': 'delete', 'node': 'img'}], **G}
        )
    )
    check('apply_edits', 'bitmap: a second op on the same file reuses the link', 'reusing bitmap resource' in t, t)
    r_ = await c('compare_to_reference', {'node_id': bm, 'reference_path': png, 'aligned': True, **G})
    t = text(r_)
    check(
        'compare_to_reference',
        'same image matches',
        'EMD 0.000' in t and 'mean abs diff 0.0000' in t and any(x.type == 'image' for x in r_.content),
        t,
    )
    darker = os.path.join(scratch, 'selftest_darker.png')
    Image.new('RGB', (128, 64), (100, 50, 25)).save(darker)
    t = text(await c('compare_to_reference', {'node_id': bm, 'reference_path': darker, **G}))
    check('compare_to_reference', 'shift measured', 'R     0.784' in t and 'mean -0.392' in t, t)
    r_ = await c('compare_to_reference', {'node_id': bm, 'reference_path': png, 'region': [100, 100, 120, 120], **G})
    check('compare_to_reference', 'error on empty region', r_.is_error and 'is empty' in text(r_), text(r_))
    r_ = await c('apply_edits', {'ops': [{'op': 'bitmap', 'path': os.path.join(scratch, 'missing.png')}], **G})
    check('apply_edits', 'bitmap: error on missing file', r_.is_error and 'no such file' in text(r_), '')
    # imported RGB JPGs and grey+alpha PNGs compute as RGBA8, like RGBA files; the other
    # pixel layouts are decoded too, but Designer's outputs weren't seen using them (REVIEW.md SRV-8)
    jpg, la_png = os.path.join(scratch, 'selftest_rgb.jpg'), os.path.join(scratch, 'selftest_la.png')
    Image.new('RGB', (8, 8), (200, 100, 50)).save(jpg, quality=100)
    la = Image.new('LA', (8, 8), (128, 255))
    la.paste((0, 0), (4, 0, 8, 8))  # right half transparent
    la.save(la_png)
    formats = []
    for path in (jpg, la_png):
        extra_bm = added_id(text(await c('apply_edits', {'ops': [{'op': 'bitmap', 'path': path}], **G})))
        formats.append(text(await c('node_stats', {'node_id': extra_bm, **G})).splitlines()[0].split()[-1])
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': extra_bm}], **G})
    check('designer facts', 'imported JPG and grey+alpha PNG compute as RGBA8', formats == ['RGBA8'] * 2, str(formats))
    # a grey+alpha reference's transparent half is ignored (REVIEW.md SRV-9)
    t = text(await c('compare_to_reference', {'node_id': bm, 'reference_path': la_png, **G}))
    check(
        'compare_to_reference',
        'grey+alpha reference: transparent pixels ignored',
        'ignoring 50.0% transparent reference pixels' in t,
        t.splitlines()[1] if '\n' in t else t,
    )


async def check_analyze_reference(ctx: Ctx) -> None:
    """analyze_reference reads a palette from an image file alone: two swatches and a transparent strip in the region
    read, a blue swatch outside it. Every parameter is given."""
    from PIL import Image

    c = ctx.c
    photo = os.path.join(ctx.scratch, 'selftest_palette.png')
    image = Image.new('RGBA', (40, 10), (0, 255, 0, 0))  # transparent green, at x 20 to 30
    image.paste((40, 20, 10, 255), (0, 0, 10, 10))
    image.paste((240, 230, 180, 255), (10, 0, 20, 10))
    image.paste((0, 0, 255, 255), (30, 0, 40, 10))
    image.save(photo)
    t = text(await c('analyze_reference', {'reference_path': photo, 'reference_region': [0, 0, 30, 10], 'keys': 3}))
    line = re.search(r'^gradientrgba: (.*)$', t, re.M)
    # the two swatches' colours, alpha 1, to the 4 decimals the result prints
    expected = [
        [p, [round(v / 255, 4) for v in rgb] + [1.0]] for p, rgb in ((0.0, (40, 20, 10)), (1.0, (240, 230, 180)))
    ]
    check(
        'analyze_reference',
        'the keys of the region, its transparent pixels left out',
        line is not None
        and json.loads(line.group(1)) == expected
        and 'selftest_palette.png: 30x10 pixels in reference_region [0, 0, 30, 10]' in t
        and 'ignoring 33.3% transparent reference pixels' in t
        and 'keys: 2 of the 3 asked' in t
        and 'fit error 0.0000:' in t,
        t,
    )


async def check_designer_greys(ctx: Ctx) -> None:
    """What the nodes an agent would turn a colour image grey with give for known colours, 32-bit float: the greys of
    palettes.expected_greys, Grayscale Conversion at its default giving the weights analyze_reference prints; and
    Grayscale Conversion's default weights, as describe_node shows them (GUIDE.md, The greys of a colour image)."""
    c, G = ctx.c, ctx.G
    t = text(await c('describe_node', {'definition': 'grayscaleconversion'}))
    shown = re.search(r'^\s+channelsweights\s+float4\b.* default=(.*)$', t, re.M)
    check(
        'designer facts',
        "greys: Grayscale Conversion's default weights",
        shown is not None and shown.group(1) == '(0.33, 0.33, 0.33, 0.0)',
        shown.group(0) if shown else t,
    )
    path = strip(os.path.join(ctx.scratch, 'selftest_strip.png'))
    weights = palette(text(await c('analyze_reference', {'reference_path': path}))).weights
    greys = expected_greys(weights)
    ops: list[dict[str, JsonSent]] = [{'op': 'bitmap', 'path': path, 'ref': 'strip'}]
    for i, grey in enumerate(greys):
        ops += [
            {
                'op': 'add',
                'definition': grey.definition,
                'ref': 'grey%d' % i,
                'params': {'$format': 'hdr_high_precision', **grey.params},
            },
            {'op': 'connect', 'from': 'strip', 'to': 'grey%d' % i, 'input': grey.connector},
        ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    for i, grey in enumerate(greys):
        t = text(await c('node_stats', {'node_id': added['grey%d' % i], 'points': strip_points(), **G}))
        got = [v[0] for v in pixel_values(t).values()]
        want = [grey.of((r / 255, g / 255, b / 255)) for r, g, b in STRIP]
        check(
            'designer facts',
            'greys: %s' % grey.said,
            near(got, want, 1e-3) and 'LUM32F' in t,
            '%s, wanted %s: %s' % (got, want, t),
        )
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': node} for node in added.values()], **G})


async def check_photo_to_gradient_map(ctx: Ctx) -> None:
    """The recipe in analyze_reference's description, end to end: a synthetic photo's palette
    (analyze_reference), its keys set on two Gradient Maps through apply_edits' set. One maps a grey ramp from 0 to 1:
    each pixel is the keys' colour at its grey. The other maps the photo's own grey, Grayscale Conversion at its
    default, through a levels from the luminance range the palette prints to 0..1: against the photo, its error is the
    printed fit error."""
    c, G = ctx.c, ctx.G
    path = photo(os.path.join(ctx.scratch, 'selftest_photo.png'))
    found = palette(text(await c('analyze_reference', {'reference_path': path, 'keys': len(RAMP)})))
    keys: list[JsonSent] = [[position, list(colour)] for position, colour in found.keys]
    ops: list[dict[str, JsonSent]] = [
        {'op': 'add', 'definition': 'pixelprocessor', 'ref': 'ramp', 'params': {'colorswitch': False}},
        {'op': 'add', 'definition': 'gradient', 'ref': 'on_ramp'},
        {'op': 'connect', 'from': 'ramp', 'to': 'on_ramp', 'input': 'input1'},
        {'op': 'bitmap', 'path': path, 'ref': 'photo'},
        {'op': 'add', 'definition': 'grayscaleconversion', 'ref': 'grey'},
        {
            'op': 'add',
            'definition': 'levels',
            'ref': 'stretch',
            'params': {'levelinlow': [found.low] * 4, 'levelinhigh': [found.high] * 4},
        },
        {'op': 'add', 'definition': 'gradient', 'ref': 'on_photo'},
        {'op': 'connect', 'from': 'photo', 'to': 'grey', 'input': 'input1'},
        {'op': 'connect', 'from': 'grey', 'to': 'stretch', 'input': 'input1'},
        {'op': 'connect', 'from': 'stretch', 'to': 'on_photo', 'input': 'input1'},
        {'op': 'set', 'node': 'on_ramp', 'params': {'gradientrgba': keys}},
        {'op': 'set', 'node': 'on_photo', 'params': {'gradientrgba': keys}},
    ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    made = await c('set_function', {'expression': '$pos.x', 'node_id': added['ramp'], **G})
    points: list[JsonSent] = [[x, 10] for x in (20, 100, 200, 256, 330, 420, 500)]
    t = text(await c('node_stats', {'node_id': added['ramp'], 'points': points, **G}))
    ramp = [v[0] for v in pixel_values(t).values()]
    t = text(await c('node_stats', {'node_id': added['on_ramp'], 'points': points, **G}))
    got = list(pixel_values(t).values())
    positions = [p for p, _ in found.keys]
    want = [[float(np.interp(g, positions, [k[i] for _, k in found.keys])) for i in range(4)] for g in ramp]
    # the ramp runs from below the second key to above 0.9, so the colours compared span the keys (REVIEW.md TST-774)
    spans = (
        not made.is_error
        and len(ramp) == len(points)
        and ramp == sorted(ramp)
        and ramp[0] < positions[1]
        and ramp[-1] > 0.9
    )
    check(
        'analyze_reference',
        'its keys set on a Gradient Map: a grey ramp computes their colours',
        spans
        and len(found.keys) == len(RAMP)
        and len(got) == len(points)
        and all(near(a, b) for a, b in zip(got, want, strict=True)),
        'the ramp %s (%s); %s, wanted %s (within %.4f)' % (ramp, text(made).strip()[-80:], got, want, CLOSE),
    )
    t = text(
        await c('compare_to_reference', {'node_id': added['on_photo'], 'reference_path': path, 'aligned': True, **G})
    )
    error = rgb_rmse(t)
    check(
        'analyze_reference',
        "the photo's grey, levelled from the printed range, through its keys: the photo within the fit error",
        error is not None and abs(error - found.error) <= 0.002 and found.error > 0.01,
        'error %s, the fit error %.4f: %s' % (error, found.error, t),
    )
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': node} for node in added.values()], **G})


# bilinear: pixel x of a 50x10 image stretched to 64 px has its centre at (x + 0.5) * 50 / 64 - 0.5 of the image, its
# share of blue the part past pixel 24, the last red one
_STRETCHED = [float(np.clip((x + 0.5) * 50 / 64 - 0.5 - 24, 0, 1)) for x in range(29, 35)]
# a 9000x10 image shrunk to 8192 px: pixels 4093 to 4098, measured 2026-11-23 (an 8-bit step's 10/255 at the edge)
_SHRUNK = [0.0, 0.0, 10 / 255, 245 / 255, 1.0, 1.0]


async def check_a_bitmap_computes_at_sides_of_powers_of_2(ctx: Ctx) -> None:
    """Bitmap nodes of images red on their left half and blue on their right. A 50x10 image: its $outputsize is each
    side's log2 rounded up, (6, 4), and the result says so. It computes 64x16, the image stretched to it with a
    bilinear filter: the halves meet at x 32, and pixels 31 and 32 blend them as their centres fall between the
    image's pixels 24 and 25. A 9000x10 image: $outputsize (14, 4), the result saying a side computes 8192 px at most,
    and it computes 8192x16, the image shrunk to it: the halves meet at x 4096, pixels 4095 and 4096 blended
    (GUIDE.md's scripting part, Bitmaps; REVIEW.md SRV-237, SRV-239)."""
    from PIL import Image

    c, G = ctx.c, ctx.G
    for width, size, computed, said, blue in (
        (50, '(6, 4)', 64, 'rounded up: the image is stretched to it; set', _STRETCHED),
        (9000, '(14, 4)', 8192, 'a side computes 8192 px at most (13): the image is shrunk to it', _SHRUNK),
    ):
        path = os.path.join(ctx.scratch, 'selftest_%dx10.png' % width)
        image = Image.new('RGB', (width, 10), (0, 0, 255))
        image.paste((255, 0, 0), (0, 0, width // 2, 10))
        image.save(path)
        t = text(await c('apply_edits', {'ops': [{'op': 'bitmap', 'path': path}], **G}))
        node = added_id(t)
        check(
            'apply_edits',
            'bitmap: a %dx10 image, its size and how it computes, the result says' % width,
            ('size %s (log2 of each side' % size) in t and said in t,
            t,
        )
        xs = range(computed // 2 - 3, computed // 2 + 3)
        t = text(await c('node_stats', {'node_id': node, 'points': [[x, 8] for x in xs], **G}))
        got = [v[:3] for v in pixel_values(t).values()]
        want = [[1 - b, 0.0, b] for b in blue]
        check(
            'designer facts',
            'a %dx10 bitmap computes %dx16, the halves meeting at x %d with 2 pixels blended'
            % (width, computed, computed // 2),
            '%dx16' % computed in t
            and len(got) == len(want)
            and all(near(a, b) for a, b in zip(got, want, strict=True)),
            '%s, wanted %s: %s' % (got, want, t),
        )
        await c('apply_edits', {'ops': [{'op': 'delete', 'node': node}], **G})


# the files of check_a_bitmap_turns_a_jpeg_by_its_orientation_and_no_other_format: (what it is, its file's name, the
# format Pillow saves it in, its EXIF orientation, the turn its bitmap node is to show, or None for the stored frame).
# Each turn is the EXIF one for its orientation: 3 a half turn, 6 a quarter clockwise, 8 a quarter anticlockwise. An MPO
# is the multi-picture JPEG some phones save, as .jpg
ORIENTED: tuple[tuple[str, str, Literal['JPEG', 'MPO', 'PNG', 'TIFF'], int, Transpose | None], ...] = (
    ('a JPEG, orientation 6', 'o6.jpg', 'JPEG', 6, Transpose.ROTATE_270),
    ('a JPEG, orientation 3', 'o3.jpg', 'JPEG', 3, Transpose.ROTATE_180),
    ('a JPEG, orientation 8', 'o8.jpg', 'JPEG', 8, Transpose.ROTATE_90),
    ('a multi-picture JPEG (MPO), orientation 6', 'o6_mpo.jpg', 'MPO', 6, Transpose.ROTATE_270),
    ('a PNG, orientation 6 (eXIf)', 'o6.png', 'PNG', 6, None),
    ('a TIFF, orientation 6', 'o6.tif', 'TIFF', 6, None),
)


async def check_a_bitmap_turns_a_jpeg_by_its_orientation_and_no_other_format(ctx: Ctx) -> None:
    """A bitmap node of a 64x32 image, red on its left half and blue on its right, a green 8x8 mark in its top-left
    corner, saved with an EXIF orientation. The mark tells a turn from its mirror (6 from 5, 8 from 7, 3 from 2).
    Designer turns a JPEG, and an MPO, as its orientation says, and computes a PNG and a TIFF as stored:
    compare_to_reference(aligned=True) of each node against the image so turned by hand, a JPEG's own decode turned,
    finds them equal (GUIDE.md's scripting part, Bitmaps; REVIEW.md SRV-238, TST-787). That the tools read each file
    so, image_reading.py's _open_image, the unit tests of test_image_reading.py check against the same turns."""
    from PIL import ExifTags, Image

    c, G = ctx.c, ctx.G
    image = Image.new('RGB', (64, 32), (0, 0, 255))
    image.paste((255, 0, 0), (0, 0, 32, 32))
    image.paste((0, 255, 0), (0, 0, 8, 8))
    for _, name, form, orientation, turn in ORIENTED:
        path = os.path.join(ctx.scratch, name)
        exif = Image.Exif()
        exif[ExifTags.Base.Orientation] = orientation
        if form == 'MPO':
            image.save(path, form, exif=exif, quality=100, subsampling=0, save_all=True, append_images=[image.copy()])
        elif form == 'JPEG':
            image.save(path, form, exif=exif, quality=100, subsampling=0)
        else:
            image.save(path, form, exif=exif)
        # the image as its node is to compute it, as a PNG with no orientation: a JPEG's own decode, which Pillow
        # doesn't turn as it loads it, turned by hand; else the image saved, not Pillow's reading of a TIFF, which
        # turns it as it loads it
        if turn is None:
            image.save(_expected(ctx, name))
        else:
            with Image.open(path) as saved:
                saved.convert('RGB').transpose(turn).save(_expected(ctx, name))
    ops: list[dict[str, JsonSent]] = [
        {'op': 'bitmap', 'path': os.path.join(ctx.scratch, name), 'ref': 'file%d' % i}
        for i, (_, name, *_) in enumerate(ORIENTED)
    ]
    added = refs(text(await c('apply_edits', {'ops': ops, **G})))
    for i, (said, name, _, _, turn) in enumerate(ORIENTED):
        args: ToolArgs = {'node_id': added['file%d' % i], 'reference_path': _expected(ctx, name), 'aligned': True, **G}
        t = text(await c('compare_to_reference', args))
        error = rgb_rmse(t)
        check(
            'designer facts',
            'a bitmap of %s computes %s' % (said, 'turned' if turn is not None else 'as stored'),
            error is not None and error < 0.01 and 'aspect ratios differ' not in t,
            t,
        )
    await c('apply_edits', {'ops': [{'op': 'delete', 'node': node} for node in added.values()], **G})


def _expected(ctx: Ctx, name: str) -> str:
    """Where check_a_bitmap_turns_a_jpeg_by_its_orientation_and_no_other_format writes the image a file's node is to
    compute."""
    return os.path.join(ctx.scratch, 'expected_%s.png' % name)
