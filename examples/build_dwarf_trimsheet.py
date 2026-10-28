"""
Dwarf stonework trim sheet generator for Substance 3D Designer (sd API).

Run inside Designer: Windows > Python Editor > open this file > Run.
Builds a new package with a 2048x2048 compositing graph and saves it to OUT_SBS.

Layout (pixels from the top, all strips tile horizontally):
    A    0- 256  stepped cornice / coping
    B  256- 512  large ashlar blocks
    C  512- 704  lattice band (diamond openwork)
    D  704- 768  stepped bead
    E  768-1024  diamond medallion plaques
    F 1024-1152  small block course
    G 1152-1280  chamfered plain band
    H 1280-1536  running-bond bricks (2 rows)
    I 1536-1600  V-groove trim
    J 1600-1664  round-ish bead
    K 1664-2048  wood planks (3 rows)
"""
import os
import sd
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdbasetypes import float2, float4, int2, ColorRGBA
from sd.api.sdproperty import SDPropertyCategory, SDPropertyInheritanceMethod
from sd.api.sdapplication import SDApplicationPath
from sd.api.sdvaluefloat import SDValueFloat
from sd.api.sdvaluefloat2 import SDValueFloat2
from sd.api.sdvaluefloat4 import SDValueFloat4
from sd.api.sdvalueint import SDValueInt
from sd.api.sdvalueint2 import SDValueInt2
from sd.api.sdvaluebool import SDValueBool
from sd.api.sdvaluecolorrgba import SDValueColorRGBA
from sd.api.sdvalueenum import SDValueEnum
from sd.api.sdvaluestring import SDValueString
from sd.api.sdvaluearray import SDValueArray
from sd.api.sdvalueusage import SDValueUsage
from sd.api.sdtypeusage import SDTypeUsage
from sd.api.sdusage import SDUsage
from sd.api.sdtypeenum import SDTypeEnum
from sd.api.apiexception import APIException

ERRORS = (Exception, APIException)

OUT_SBS = os.path.join(os.path.expanduser('~'), 'Documents', 'dwarf_trimsheet', 'dwarf_trimsheet.sbs')
GRAPH_ID = 'dwarf_trimsheet'
SIZE_LOG2 = 11
H = 2 ** SIZE_LOG2

# Atomic blend modes
COPY, ADD, SUBTRACT, MULTIPLY, MAX, MIN = 0, 1, 2, 3, 5, 6
# tile_generator Pattern_Type
SQUARE = 2

BEVEL_DIST = 0.04
NORMAL_INTENSITY = 6.0
NORMAL_OPENGL = True        # Blender expects OpenGL normals

STONE_LIGHT = (0.62, 0.60, 0.56)
STONE_DARK = (0.42, 0.40, 0.37)
STONE_EDGE = (0.78, 0.76, 0.72)
WOOD_LIGHT = (0.42, 0.27, 0.15)
WOOD_DARK = (0.22, 0.13, 0.07)
CAVITY = (0.08, 0.07, 0.06)
STONE_ROUGH, WOOD_ROUGH = 0.86, 0.68


class Builder:
    def __init__(self, ctx):
        self.app = ctx.getSDApplication()
        self.pkg_mgr = self.app.getPackageMgr()
        self.lib_dir = os.path.join(self.app.getPath(SDApplicationPath.DefaultResourcesDir), 'packages')
        # Close earlier builds, saved or not, so re-running doesn't pile up packages
        for p in list(self.pkg_mgr.getUserPackages()):
            if any(r.getIdentifier() == GRAPH_ID for r in p.getChildrenResources(False)):
                self.pkg_mgr.unloadUserPackage(p)
        self.pkg = self.pkg_mgr.newUserPackage()
        self.graph = SDSBSCompGraph.sNew(self.pkg)
        self.graph.setIdentifier(GRAPH_ID)
        self._set_graph_size()
        self._lib_cache = {}
        self.col = 0
        self.row = 0
        self.warnings = []

    # ---------------------------------------------------------------- basics
    def _set_graph_size(self):
        try:
            prop = self.graph.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
            self.graph.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
        except ERRORS:
            pass
        self.graph.setInputPropertyValueFromId('$outputsize', SDValueInt2.sNew(int2(SIZE_LOG2, SIZE_LOG2)))

    def _place(self, node):
        node.setPosition(float2(self.col * 160.0, self.row * 160.0))
        self.col += 1
        return node

    def _force_16bit(self, node):
        try:
            node.setInputPropertyInheritanceMethodFromId('$format', SDPropertyInheritanceMethod.Absolute)
            node.setInputPropertyValueFromId('$format', SDValueEnum.sFromValueId('sbs::compositing::format', '16_bits_per_channel'))
        except ERRORS:
            pass

    def atomic(self, name, **params):
        node = self._place(self.graph.newNode('sbs::compositing::' + name))
        self._force_16bit(node)
        for k, v in params.items():
            self.set(node, k, v)
        return node

    def lib(self, pkg_file, graph_id, **params):
        res = self._lib_resource(pkg_file, graph_id)
        node = self._place(self.graph.newInstanceNode(res))
        self._force_16bit(node)
        for k, v in params.items():
            self.set(node, k, v)
        return node

    def _lib_resource(self, pkg_file, graph_id):
        key = (pkg_file, graph_id)
        if key not in self._lib_cache:
            path = os.path.join(self.lib_dir, pkg_file)
            pkg = None
            for p in self.pkg_mgr.getPackages():
                fp = p.getFilePath() or ''
                if os.path.normpath(fp) == os.path.normpath(path):
                    pkg = p
                    break
            if pkg is None:
                pkg = self.pkg_mgr.loadUserPackage(path)
            res = pkg.findResourceFromUrl(graph_id)
            if res is None:
                raise RuntimeError('Graph %s not found in %s' % (graph_id, path))
            self._lib_cache[key] = res
        return self._lib_cache[key]

    def set(self, node, prop_id, v):
        prop = node.getPropertyFromId(prop_id, SDPropertyCategory.Input)
        if prop is None:
            self.warnings.append('no input %s on %s' % (prop_id, node.getDefinition().getId()))
            return
        ptype = prop.getType()
        if isinstance(ptype, SDTypeEnum) and isinstance(v, int) and not isinstance(v, bool):
            for e in ptype.getEnumerators():
                if e.getDefaultValue().get() == v:
                    node.setPropertyValue(prop, e.getDefaultValue())
                    return
            self.warnings.append('enum value %d not found for %s' % (v, prop_id))
            return
        if isinstance(v, bool):
            candidates = [lambda: SDValueBool.sNew(v)]
        elif isinstance(v, int):
            candidates = [lambda: SDValueInt.sNew(v), lambda: SDValueFloat.sNew(float(v))]
        elif isinstance(v, float):
            candidates = [lambda: SDValueFloat.sNew(v)]
        elif len(v) == 2 and all(isinstance(x, int) for x in v):
            candidates = [lambda: SDValueInt2.sNew(int2(*v))]
        elif len(v) == 2:
            candidates = [lambda: SDValueFloat2.sNew(float2(*v))]
        else:
            c = tuple(v) + (1.0,) * (4 - len(v))
            candidates = [lambda: SDValueColorRGBA.sNew(ColorRGBA(*c)), lambda: SDValueFloat4.sNew(float4(*c))]
        for make in candidates:
            try:
                node.setInputPropertyValueFromId(prop_id, make())
                return
            except ERRORS:
                continue
        self.warnings.append('could not set %s=%r on %s' % (prop_id, v, node.getDefinition().getId()))

    @staticmethod
    def _output_id(node, name=None):
        outs = node.getProperties(SDPropertyCategory.Output)
        ids = [outs.getItem(i).getId() for i in range(outs.getSize())]
        if name:
            return name
        return ids[0]

    def link(self, src, dst, dst_input, src_output=None):
        src.newPropertyConnectionFromId(self._output_id(src, src_output), dst, dst_input)
        return dst

    # ------------------------------------------------------- height building
    def gy(self, y):
        # gradient_linear_1 (rotation 0) is 1.0 at the top row, 0.0 at the bottom
        return 1.0 - float(y) / H

    def levels(self, src, in_lo=0.0, in_hi=1.0, out_lo=0.0, out_hi=1.0):
        n = self.atomic('levels',
                        levelinlow=(in_lo,) * 4, levelinhigh=(in_hi,) * 4,
                        leveloutlow=(out_lo,) * 4, levelouthigh=(out_hi,) * 4)
        return self.link(src, n, 'input1')

    def ramp(self, y_from, y_to, h):
        """0 at row y_from rising linearly to h at row y_to, clamped beyond."""
        if y_from < y_to:
            return self.levels(self.grad, self.gy(y_to), self.gy(y_from), h, 0.0)
        return self.levels(self.grad, self.gy(y_from), self.gy(y_to), 0.0, h)

    def band(self, y0, y1, h, bevel_top=1, bevel_bottom=None):
        """Horizontal plateau of height h between rows y0 and y1 with chamfered edges."""
        bevel_bottom = bevel_top if bevel_bottom is None else bevel_bottom
        top = self.ramp(y0, y0 + max(bevel_top, 1), h)
        bottom = self.ramp(y1, y1 - max(bevel_bottom, 1), h)
        return self.blend(top, bottom, MIN)

    def blend(self, src, dst, mode, opacity=1.0, mask=None):
        n = self.atomic('blend', blendingmode=mode, opacitymult=opacity)
        self.link(src, n, 'source')
        self.link(dst, n, 'destination')
        if mask is not None:
            self.link(mask, n, 'opacity')
        return n

    def max_all(self, nodes):
        acc = nodes[0]
        for n in nodes[1:]:
            acc = self.blend(n, acc, MAX)
        return acc

    def tiles(self, nb_x, nb_y, scale, offset=0.0, offset_random=0.0, rotation=0.0, seed=0, luminance_random=0.0):
        return self.lib('tile_generator.sbs', 'tile_generator',
                        Nb_X=nb_x, Nb_Y=nb_y, Pattern_Type=SQUARE, Scale=scale,
                        Offset=offset, Offset_Random=offset_random, Offset_Random_Seed=seed,
                        Free_Rotation=rotation, **{'Luminance_Variation-Contrast': (luminance_random, 0.0)})

    def bevel(self, src, distance=BEVEL_DIST, smoothing=0.0):
        n = self.lib('bevel.sbs', 'bevel', distance=distance, smoothing=smoothing)
        return self.link(src, n, 'input')

    def clip(self, height, y0, y1):
        """Keep `height` only inside rows y0..y1."""
        return self.blend(height, self.band(y0, y1, 1.0, 1), MIN)

    def blocks(self, y0, y1, nb_x, nb_y, scale, h, offset=0.0, seed=0, mortar=0.12):
        t = self.bevel(self.tiles(nb_x, nb_y, scale, offset=offset, offset_random=0.35, seed=seed))
        raised = self.clip(self.levels(t, out_hi=h), y0, y1)
        return self.blend(raised, self.band(y0, y1, mortar, 1), MAX)

    def next_row(self):
        self.row += 2
        self.col = 0


def build(ctx):
    b = Builder(ctx)
    b.grad = b.lib('gradient_linear_1.sbs', 'gradient_linear_1', rotation=0)
    b.next_row()
    strips = []

    # A: stepped cornice 0-256
    strips.append(b.max_all([b.band(0, 256, 0.30, 4), b.band(24, 232, 0.50, 12),
                             b.band(56, 200, 0.72, 20), b.band(92, 164, 0.88, 18)]))
    b.next_row()

    # B: large ashlar blocks 256-512 (tile rows are 256px tall, row 1)
    strips.append(b.blocks(256, 512, 5, 8, 0.955, 0.70, seed=3))
    b.next_row()

    # C: lattice band 512-704 (64px diamond cells, centre row at 608)
    frame = b.band(512, 704, 0.55, 8)
    hole = b.band(540, 676, 0.25, 6)
    framed = b.blend(hole, frame, SUBTRACT)
    diamonds = b.tiles(32, 32, 0.55, rotation=45.0)
    ribs = b.clip(b.levels(diamonds, out_lo=0.48, out_hi=0.22), 540, 676)
    strips.append(b.blend(ribs, framed, MAX))
    b.next_row()

    # D: stepped bead 704-768
    strips.append(b.max_all([b.band(704, 768, 0.35, 3), b.band(712, 760, 0.55, 10),
                             b.band(722, 750, 0.66, 8)]))
    b.next_row()

    # E: medallion plaques 768-1024 (256px cells, centre row at 896)
    base = b.band(768, 1024, 0.42, 8)
    plaque = b.levels(b.bevel(b.tiles(8, 8, 0.74)), out_hi=0.62)
    inset = b.levels(b.tiles(8, 8, 0.56), out_hi=0.10)
    plaque = b.blend(inset, plaque, SUBTRACT)
    diamond = b.levels(b.bevel(b.tiles(8, 8, 0.36, rotation=45.0)), out_hi=0.78)
    strips.append(b.clip(b.max_all([base, plaque, diamond]), 768, 1024))
    b.next_row()

    # F: small block course 1024-1152 (128px rows, row 8)
    strips.append(b.blocks(1024, 1152, 12, 16, 0.94, 0.60, offset=0.5, seed=7))
    b.next_row()

    # G: chamfered plain band 1152-1280
    strips.append(b.band(1152, 1280, 0.60, 24))
    b.next_row()

    # H: running-bond bricks 1280-1536 (128px rows, rows 10-11)
    strips.append(b.blocks(1280, 1536, 8, 16, 0.95, 0.65, offset=0.5, seed=11))
    b.next_row()

    # I: V-groove trim 1536-1600
    strips.append(b.blend(b.band(1556, 1580, 0.30, 12), b.band(1536, 1600, 0.60, 4), SUBTRACT))
    b.next_row()

    # J: round-ish bead 1600-1664
    strips.append(b.max_all([b.band(1600, 1664, 0.30, 6), b.band(1608, 1656, 0.50, 14),
                             b.band(1618, 1646, 0.60, 8)]))
    b.next_row()

    # K: wood planks 1664-2048 (128px rows, rows 13-15)
    # Rows get their own chamfered band so the long seams read as V-grooves
    rows = b.max_all([b.band(1664, 1792, 0.5, 6), b.band(1792, 1920, 0.5, 6), b.band(1920, 2048, 0.5, 6)])
    # Same layout/seed twice: once for end-joint bevels, once for a random grey per plank
    plank_layout = dict(offset_random=0.5, seed=5)
    ends = b.levels(b.bevel(b.tiles(3, 16, 0.99, **plank_layout), distance=0.02), out_hi=0.5)
    plank_id = b.tiles(3, 16, 1.0, luminance_random=1.0, **plank_layout)
    # Grain shifted vertically by a different amount per plank, so it breaks at every joint
    raw_grain = b.lib('noise_anisotropic_noise.sbs', 'anisotropic_noise', X_Amount=3, Y_Amount=96)
    wavy = b.link(raw_grain, b.atomic('warp', intensity=0.08), 'input1')
    b.link(b.lib('noise_clouds_2.sbs', 'clouds_2', scale=2), wavy, 'inputgradient')
    grain = b.link(wavy, b.atomic('directionalwarp', intensity=60.0, warpangle=0.25), 'input1')
    b.link(plank_id, grain, 'inputintensity')
    planks = b.blend(ends, rows, MIN)
    planks = b.blend(b.levels(grain, out_hi=0.05), planks, SUBTRACT)
    strips.append(b.clip(planks, 1664, 2048))
    b.next_row()

    # ---------------------------------------------------------- combine
    height = b.max_all(strips)
    wood_mask = b.band(1664, 2048, 1.0, 1)
    stone_mask = b.levels(wood_mask, out_lo=1.0, out_hi=0.0)
    clouds = b.lib('noise_clouds_2.sbs', 'clouds_2', scale=4)
    height = b.blend(b.levels(clouds, out_hi=0.05), height, SUBTRACT, mask=stone_mask)
    b.next_row()

    normal = b.link(height, b.atomic('normal', intensity=NORMAL_INTENSITY, inversedy=NORMAL_OPENGL), 'input1')
    ao = b.link(height, b.lib('hbao.sbs', 'hbao', height_depth=0.12, radius=1.0), 'input')
    curvature = b.link(normal, b.lib('curvature_smooth.sbs', 'curvature_smooth',
                                     normal_format=0 if NORMAL_OPENGL else 1), 'input')
    b.next_row()

    # ---------------------------------------------------------- base color
    def uni(rgb):
        return b.atomic('uniform', colorswitch=True, outputcolor=rgb)

    stone = b.blend(uni(STONE_LIGHT), uni(STONE_DARK), COPY, mask=clouds)
    grime = b.lib('noise_grunge_map_002.sbs', 'grunge_map_002')
    stone = b.blend(uni(STONE_DARK), stone, COPY, opacity=0.35, mask=grime)
    edges = b.levels(curvature, in_lo=0.52, in_hi=0.62)
    stone = b.blend(uni(STONE_EDGE), stone, COPY, opacity=0.7, mask=edges)
    wood = b.blend(uni(WOOD_LIGHT), uni(WOOD_DARK), COPY, mask=grain)
    wood = b.blend(uni(WOOD_DARK), wood, COPY, opacity=0.45, mask=plank_id)
    color = b.blend(wood, stone, COPY, mask=wood_mask)
    cavity = b.levels(ao, out_lo=0.85, out_hi=0.0)
    color = b.blend(uni(CAVITY), color, COPY, mask=cavity)
    b.next_row()

    # ---------------------------------------------------------- roughness / metallic
    def gray(v):
        return b.atomic('uniform', colorswitch=False, outputcolor=(v, v, v, 1.0))

    rough = b.blend(gray(WOOD_ROUGH), gray(STONE_ROUGH), COPY, mask=wood_mask)
    rough = b.blend(b.levels(grime, out_hi=0.08), rough, SUBTRACT)
    rough = b.blend(b.levels(edges, out_hi=0.06), rough, SUBTRACT)
    metallic = gray(0.0)
    b.next_row()

    # ---------------------------------------------------------- outputs
    outputs = [('basecolor', 'baseColor', 'RGBA', 'sRGB', color),
               ('normal', 'normal', 'RGBA', 'Linear', normal),
               ('roughness', 'roughness', 'R', 'Linear', rough),
               ('metallic', 'metallic', 'R', 'Linear', metallic),
               ('height', 'height', 'R', 'Linear', height),
               ('ambientocclusion', 'ambientOcclusion', 'R', 'Linear', ao)]
    for ident, usage, comps, space, src in outputs:
        out = b.atomic('output')
        usages = SDValueArray.sNew(SDTypeUsage.sNew(), 0)
        usages.pushBack(SDValueUsage.sNew(SDUsage.sNew(usage, comps, space)))
        out.setAnnotationPropertyValueFromId('usages', usages)
        out.setAnnotationPropertyValueFromId('identifier', SDValueString.sNew(ident))
        out.setAnnotationPropertyValueFromId('label', SDValueString.sNew(ident))
        b.link(src, out, 'inputNodeOutput')

    os.makedirs(os.path.dirname(OUT_SBS), exist_ok=True)
    b.pkg_mgr.savePackageAs(b.pkg, OUT_SBS)
    print('Saved trim sheet to %s (%d nodes)' % (OUT_SBS, b.graph.getNodes().getSize()))
    for w in b.warnings:
        print('WARNING:', w)


build(sd.getContext())
