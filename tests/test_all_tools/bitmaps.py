"""Bitmaps: import_bitmap and compare_to_reference."""

import os

from .common import Ctx, added_id, check, text


async def run(ctx: Ctx) -> None:
    c, scratch, G = ctx.c, ctx.scratch, ctx.G
    # --- bitmaps
    from PIL import Image

    png = os.path.join(scratch, 'selftest_bitmap.png')
    Image.new('RGB', (64, 32), (200, 100, 50)).save(png)
    t = text(await c('import_bitmap', {'path': png, 'position': [-600, 300], **G}))
    check('import_bitmap', 'linked, native size', 'size (6, 5)' in t, t)
    bm = added_id(t)
    t = text(await c('node_stats', {'node_id': bm, 'points': [[0, 0]], **G}))
    check('import_bitmap', 'pixels match file', 'R=0.7843, G=0.3922, B=0.1961' in t, t)
    t = text(
        await c(
            'apply_edits', {'ops': [{'op': 'bitmap', 'path': png, 'ref': 'img'}, {'op': 'delete', 'node': 'img'}], **G}
        )
    )
    check('import_bitmap', 'apply_edits op, link reused', 'reusing bitmap resource' in t, t)
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
    r_ = await c('import_bitmap', {'path': os.path.join(scratch, 'missing.png'), **G})
    check('import_bitmap', 'error on missing file', r_.is_error and 'no such file' in text(r_), '')
    # imported RGB JPGs and grey+alpha PNGs compute as RGBA8, like RGBA files; the other
    # pixel layouts are decoded too, but Designer's outputs weren't seen using them (REVIEW.md SRV-8)
    jpg, la_png = os.path.join(scratch, 'selftest_rgb.jpg'), os.path.join(scratch, 'selftest_la.png')
    Image.new('RGB', (8, 8), (200, 100, 50)).save(jpg, quality=100)
    la = Image.new('LA', (8, 8), (128, 255))
    la.paste((0, 0), (4, 0, 8, 8))  # right half transparent
    la.save(la_png)
    formats = []
    for path in (jpg, la_png):
        extra_bm = added_id(text(await c('import_bitmap', {'path': path, **G})))
        formats.append(text(await c('node_stats', {'node_id': extra_bm, **G})).splitlines()[0].split()[-1])
        await c('delete_nodes', {'node_ids': [extra_bm], **G})
    check('designer facts', 'imported JPG and grey+alpha PNG compute as RGBA8', formats == ['RGBA8'] * 2, str(formats))
    # a grey+alpha reference's transparent half is ignored (REVIEW.md SRV-9)
    t = text(await c('compare_to_reference', {'node_id': bm, 'reference_path': la_png, **G}))
    check(
        'compare_to_reference',
        'grey+alpha reference: transparent pixels ignored',
        'ignoring 50.0% transparent reference pixels' in t,
        t.splitlines()[1] if '\n' in t else t,
    )
    ctx.png = png
