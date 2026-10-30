"""
Dwarf stonework trim sheet generator for Substance 3D Designer (sd API).

Run inside Designer: Windows > Python Editor > open this file > Run (or the run_designer_script
tool). Builds a new package with a 2048x2048 compositing graph and saves it to OUT_SBS.

The graph is laid out for reading: one titled frame per section (a frame per strip, then the
height, normal/AO, base colour, roughness and output stages) whose description explains the
non-obvious choices, nodes left to right by data flow inside each frame, and portals instead of the long wires
between sections (the shared gradient alone feeds about 60 inputs). The size follows the parent
(2048 by default), so renders can override it.

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
import xml.etree.ElementTree as ET
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
from sd.api.sdgraphobjectframe import SDGraphObjectFrame
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

# Graph layout (graph units; a node is 96x96 and positions are node centres)
NODE, DX, DY = 96.0, 200.0, 150.0      # node size, column and row spacing inside a section
MARGIN, TITLE_BAR = 40.0, 30.0         # frame padding around its nodes, room for the frame title
SECTION_GAP, COLUMN_GAP = 80.0, 240.0  # between stacked frames, between columns of frames
PORTAL_LONGER_THAN = 1000.0            # a link between sections longer than this becomes a portal,
PORTAL_FANOUT = 4                      # and so does one from an output feeding this many inputs
STONE_FRAME = (0.45, 0.45, 0.50, 0.25)
WOOD_FRAME = (0.55, 0.36, 0.20, 0.25)
MAPS_FRAME = (0.25, 0.38, 0.55, 0.25)
OUT_FRAME = (0.25, 0.50, 0.32, 0.25)


class Builder:
    def __init__(self, ctx):
        self.app = ctx.getSDApplication()
        self.pkg_mgr = self.app.getPackageMgr()
        self.lib_dir = os.path.join(self.app.getPath(SDApplicationPath.DefaultResourcesDir), 'packages')
        # Close the previous build (the package saved at OUT_SBS) so re-running doesn't pile up
        # packages; never discard edits: refuse if it has unsaved changes, and leave any other
        # package with a graph of this name (a copy saved elsewhere, an unsaved one) open
        # The previous build is matched by its path, whatever its graph is called now (a renamed
        # graph still lives in the file this run writes over; REVIEW.md INS-22)
        previous = []
        out = os.path.normcase(os.path.abspath(OUT_SBS))
        for p in list(self.pkg_mgr.getUserPackages()):
            path = p.getFilePath() or ''
            if path and os.path.normcase(os.path.abspath(path)) == out:
                if p.isModified():
                    raise RuntimeError('%s has unsaved changes; save or close it before rebuilding' % OUT_SBS)
                previous.append(p)
            elif any(r.getIdentifier() == GRAPH_ID for r in p.getChildrenResources(False)):
                print('Note: left %s open; it also has a graph named %s' % (path or 'an unsaved package', GRAPH_ID))
        for p in previous:
            self.pkg_mgr.unloadUserPackage(p)
        self.pkg = self.pkg_mgr.newUserPackage()
        try:
            self.graph = SDSBSCompGraph.sNew(self.pkg)
            self.graph.setIdentifier(GRAPH_ID)
            self._set_graph_size()
        except BaseException:             # don't leave the new, unsaved package behind (REVIEW.md INS-17)
            self.pkg_mgr.unloadUserPackage(self.pkg)
            raise
        self._lib_cache = {}
        self.sections = []      # [{'title', 'column', 'color', 'description', 'nodes'}] in build order
        self.warnings = []

    # ---------------------------------------------------------------- basics
    def _set_graph_size(self):
        """Relative to the parent with a 2^SIZE_LOG2 default, so a render can override the size
        (a fixed, Absolute size isn't exposed and overrides would be ignored)."""
        prop = self.graph.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
        self.graph.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.RelativeToParent)
        self.graph.setDefaultParentSize(int2(H, H))     # pixels, not log2
        self.graph.setPropertyValue(prop, SDValueInt2.sNew(int2(0, 0)))

    def section(self, title, column, color, description=None):
        """Nodes created from now on belong to this section: one frame, laid out together."""
        self.sections.append({'title': title, 'column': column, 'color': color,
                              'description': description, 'nodes': []})

    def _place(self, node):
        self.sections[-1]['nodes'].append(node)
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

    # ------------------------------------------------------- readable graph
    def links(self):
        """(source node, source output id, target node, target input id) for every link."""
        found = []
        for node in self.graph.getNodes():
            for prop in node.getProperties(SDPropertyCategory.Input):
                if not prop.isConnectable():
                    continue
                for c in node.getPropertyConnections(prop):
                    # reported from the queried node's side: the "input" end is the other node
                    found.append((c.getInputPropertyNode(), c.getInputProperty().getId(), node, prop.getId()))
        return found

    def _arrange(self, nodes, links):
        """Columns by data flow inside one section (longest path from the section's own sources),
        each column ordered by its inputs' rows to reduce crossings. Returns {node id: (col, row)}
        and the section's size in columns and rows."""
        ids = [n.getIdentifier() for n in nodes]
        inside = set(ids)
        preds = {i: [] for i in ids}
        for src, _, dst, _ in links:
            a, b = src.getIdentifier(), dst.getIdentifier()
            if a in inside and b in inside:
                preds[b].append(a)
        layer = {i: 0 for i in ids}
        for _ in ids:                                 # longest path; at most len(ids) passes
            changed = False
            for b in ids:
                for a in preds[b]:
                    if layer[b] < layer[a] + 1:
                        layer[b], changed = layer[a] + 1, True
            if not changed:
                break
        columns = {}
        for i in ids:                                 # build order as the starting order
            columns.setdefault(layer[i], []).append(i)
        row = {}
        for L in sorted(columns):
            def bary(i, start={i: k for k, i in enumerate(columns[L])}):
                ps = [row[p] for p in preds[i] if p in row]
                return sum(ps) / len(ps) if ps else start[i]
            columns[L].sort(key=bary)
            row.update({i: k for k, i in enumerate(columns[L])})
        tallest = max(len(c) for c in columns.values())
        cells = {}
        for L, col in columns.items():
            for k, i in enumerate(col):
                cells[i] = (L, k + (tallest - len(col)) / 2.0)   # centre short columns
        return cells, len(columns), tallest

    def layout(self):
        """Place every section's nodes, stack sections in their columns, frame each section."""
        links = self.links()
        arranged = [self._arrange(s['nodes'], links) for s in self.sections]
        column_ids = sorted({s['column'] for s in self.sections})
        widths = {c: max(n_cols for s, (_, n_cols, _) in zip(self.sections, arranged) if s['column'] == c)
                  for c in column_ids}
        x0, left = {}, 0.0
        for c in column_ids:
            x0[c] = left
            left += (widths[c] - 1) * DX + NODE + 2 * MARGIN + COLUMN_GAP
        top = {c: 0.0 for c in column_ids}
        for s, (cells, n_cols, n_rows) in zip(self.sections, arranged):
            c = s['column']
            frame_top = top[c]
            first_x = x0[c] + MARGIN + NODE / 2.0
            first_y = frame_top + TITLE_BAR + MARGIN + NODE / 2.0
            for n in s['nodes']:
                L, k = cells[n.getIdentifier()]
                n.setPosition(float2(first_x + L * DX, first_y + k * DY))
            width = (n_cols - 1) * DX + NODE + 2 * MARGIN
            height = TITLE_BAR + (n_rows - 1) * DY + NODE + 2 * MARGIN
            frame = SDGraphObjectFrame.sNew(self.graph)
            frame.setTitle(s['title'])
            frame.setPosition(float2(x0[c], frame_top))
            frame.setSize(float2(width, height))
            frame.setColor(ColorRGBA(*s['color']))
            if s['description']:
                frame.setDescription(s['description'])
            top[c] = frame_top + height + SECTION_GAP

    def portal_links(self):
        """[(target node id, target input id)] to show as portals: links between sections that
        are long, or that come from an output feeding many inputs. Links inside a section stay
        wires, so each frame still reads on its own."""
        links = self.links()
        section_of = {n.getIdentifier(): k for k, s in enumerate(self.sections) for n in s['nodes']}
        fanout = {}
        for src, out, _, _ in links:
            key = (src.getIdentifier(), out)
            fanout[key] = fanout.get(key, 0) + 1
        picked = []
        for src, out, dst, inp in links:
            a, b = src.getIdentifier(), dst.getIdentifier()
            if section_of.get(a) == section_of.get(b):
                continue
            pa, pb = src.getPosition(), dst.getPosition()
            long_link = ((pa.x - pb.x) ** 2 + (pa.y - pb.y) ** 2) ** 0.5 > PORTAL_LONGER_THAN
            if long_link or fanout[(a, out)] >= PORTAL_FANOUT:
                picked.append((b, inp))
        return picked


def save_with_portals(b, portals):
    """Save the package, then mark the chosen links as portals in the saved file and load it
    again: the sd API can't set a link's display mode (a .sbs <displayType v="1"/> on the
    target node's <connection>). The new graph has never been opened in an editor view, so
    unloading it here tears down nothing (reloading a graph that is open in a view, back to
    back in one call, once crashed Designer). Returns the reloaded graph."""
    os.makedirs(os.path.dirname(OUT_SBS), exist_ok=True)
    b.pkg_mgr.savePackageAs(b.pkg, OUT_SBS)
    if not portals:
        return b.graph
    b.pkg_mgr.unloadUserPackage(b.pkg)
    tree = ET.parse(OUT_SBS)
    graph = next(g for g in tree.getroot().iter('graph') if g.find('identifier').get('v') == GRAPH_ID)
    wanted = set(portals)
    for node in graph.find('compNodes'):
        uid = node.find('uid').get('v')
        for c in node.findall('connections/connection'):
            if (uid, c.find('identifier').get('v')) in wanted:
                dt = c.find('displayType')
                if dt is None:
                    dt = ET.SubElement(c, 'displayType')
                dt.set('v', '1')
    tree.write(OUT_SBS, encoding='UTF-8', xml_declaration=True)
    pkg = b.pkg_mgr.loadUserPackage(OUT_SBS)
    return pkg.findResourceFromUrl(GRAPH_ID)


def build(ctx):
    """Build the trim sheet. If the build fails before the package was first saved, its unsaved
    package is closed, so failed runs don't leave packages with the graph's name behind."""
    b = Builder(ctx)
    try:
        build_into(b)
    except BaseException:                 # also the bridge's abort, which is raised on
        try:
            if not b.pkg.getFilePath():
                b.pkg_mgr.unloadUserPackage(b.pkg)
                print('Build failed; closed its unsaved package.')
        except ERRORS:
            pass                          # already saved and reloaded by save_with_portals
        raise


def build_into(b):
    def strip(title, desc, color=STONE_FRAME):
        # two columns of strips, A-F and G-K, so the graph isn't one very tall column
        b.section(title, 1 if title < 'G' else 2, color, desc)

    b.section('Coordinate', 0, MAPS_FRAME, 'Shared by every strip: 1.0 at the top row, 0.0 at the bottom. '
                                           'Levels on it give each strip its per-row height profile.')
    b.grad = b.lib('gradient_linear_1.sbs', 'gradient_linear_1', rotation=0)
    strips = []

    strip('A: stepped cornice', 'Rows 0-256')
    strips.append(b.max_all([b.band(0, 256, 0.30, 4), b.band(24, 232, 0.50, 12),
                             b.band(56, 200, 0.72, 20), b.band(92, 164, 0.88, 18)]))

    # B: tile rows are 256px tall, row 1
    strip('B: large ashlar blocks', 'Rows 256-512')
    strips.append(b.blocks(256, 512, 5, 8, 0.955, 0.70, seed=3))

    # C: 64px diamond cells, centre row at 608
    strip('C: lattice band', 'Rows 512-704: diamond openwork')
    frame = b.band(512, 704, 0.55, 8)
    hole = b.band(540, 676, 0.25, 6)
    framed = b.blend(hole, frame, SUBTRACT)
    diamonds = b.tiles(32, 32, 0.55, rotation=45.0)
    ribs = b.clip(b.levels(diamonds, out_lo=0.48, out_hi=0.22), 540, 676)
    strips.append(b.blend(ribs, framed, MAX))

    strip('D: stepped bead', 'Rows 704-768')
    strips.append(b.max_all([b.band(704, 768, 0.35, 3), b.band(712, 760, 0.55, 10),
                             b.band(722, 750, 0.66, 8)]))

    # E: 256px cells, centre row at 896
    strip('E: diamond medallion plaques', 'Rows 768-1024')
    base = b.band(768, 1024, 0.42, 8)
    plaque = b.levels(b.bevel(b.tiles(8, 8, 0.74)), out_hi=0.62)
    inset = b.levels(b.tiles(8, 8, 0.56), out_hi=0.10)
    plaque = b.blend(inset, plaque, SUBTRACT)
    diamond = b.levels(b.bevel(b.tiles(8, 8, 0.36, rotation=45.0)), out_hi=0.78)
    strips.append(b.clip(b.max_all([base, plaque, diamond]), 768, 1024))

    # F: 128px rows, row 8
    strip('F: small block course', 'Rows 1024-1152')
    strips.append(b.blocks(1024, 1152, 12, 16, 0.94, 0.60, offset=0.5, seed=7))

    strip('G: chamfered plain band', 'Rows 1152-1280')
    strips.append(b.band(1152, 1280, 0.60, 24))

    # H: 128px rows, rows 10-11
    strip('H: running-bond bricks', 'Rows 1280-1536: two rows')
    strips.append(b.blocks(1280, 1536, 8, 16, 0.95, 0.65, offset=0.5, seed=11))

    strip('I: V-groove trim', 'Rows 1536-1600')
    strips.append(b.blend(b.band(1556, 1580, 0.30, 12), b.band(1536, 1600, 0.60, 4), SUBTRACT))

    strip('J: round-ish bead', 'Rows 1600-1664')
    strips.append(b.max_all([b.band(1600, 1664, 0.30, 6), b.band(1608, 1656, 0.50, 14),
                             b.band(1618, 1646, 0.60, 8)]))

    # K: 128px rows, rows 13-15
    strip('K: wood planks', 'Rows 1664-2048: three rows of planks. The plank id tiles share the plank '
                            'ends\' layout and seed: a random grey per plank shifts the grain and varies '
                            'the wood colour.', WOOD_FRAME)
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

    # ---------------------------------------------------------- combine
    b.section('Height', 3, MAPS_FRAME, 'All strips combined, plus a little cloud noise on the stone')
    height = b.max_all(strips)
    wood_mask = b.band(1664, 2048, 1.0, 1)
    stone_mask = b.levels(wood_mask, out_lo=1.0, out_hi=0.0)
    clouds = b.lib('noise_clouds_2.sbs', 'clouds_2', scale=4)
    height = b.blend(b.levels(clouds, out_hi=0.05), height, SUBTRACT, mask=stone_mask)

    b.section('Normal, AO, curvature', 3, MAPS_FRAME, 'From the height; normals are OpenGL (Blender)')
    normal = b.link(height, b.atomic('normal', intensity=NORMAL_INTENSITY, inversedy=NORMAL_OPENGL), 'input1')
    ao = b.link(height, b.lib('hbao.sbs', 'hbao', height_depth=0.12, radius=1.0), 'input')
    curvature = b.link(normal, b.lib('curvature_smooth.sbs', 'curvature_smooth',
                                     normal_format=0 if NORMAL_OPENGL else 1), 'input')

    # ---------------------------------------------------------- base color
    b.section('Base colour', 3, MAPS_FRAME, 'Stone and wood tones, grime, worn edges, dark cavities')

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

    # ---------------------------------------------------------- roughness / metallic
    b.section('Roughness, metallic', 3, MAPS_FRAME, 'Stone rougher than wood; grime and worn edges a bit smoother')

    def gray(v):
        return b.atomic('uniform', colorswitch=False, outputcolor=(v, v, v, 1.0))

    rough = b.blend(gray(WOOD_ROUGH), gray(STONE_ROUGH), COPY, mask=wood_mask)
    rough = b.blend(b.levels(grime, out_hi=0.08), rough, SUBTRACT)
    rough = b.blend(b.levels(edges, out_hi=0.06), rough, SUBTRACT)
    metallic = gray(0.0)

    # ---------------------------------------------------------- outputs
    b.section('Outputs', 4, OUT_FRAME, 'Identifiers become the exported file names')
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

    b.layout()
    portals, n_links = b.portal_links(), len(b.links())
    graph = save_with_portals(b, portals)      # b.graph is closed after this; use `graph`
    print('Saved trim sheet to %s (%d nodes, %d frames, %d of %d links as portals)' % (
        OUT_SBS, graph.getNodes().getSize(), len(b.sections), len(portals), n_links))
    for w in b.warnings:
        print('WARNING:', w)


build(sd.getContext())
