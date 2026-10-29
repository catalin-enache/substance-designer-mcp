"""
Helpers executed INSIDE Substance Designer (sent over the bridge ahead of each tool call).
They only use Designer's bundled Python and the `sd` API.
"""
import os
import sd
from sd.api.apiexception import APIException
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
from sd.api.sdapplication import SDApplicationPath
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdtypeenum import SDTypeEnum

_APP = sd.getContext().getSDApplication()
_PM = _APP.getPackageMgr()


def _current_graph():
    try:
        return _APP.getQtForPythonUIMgr().getCurrentGraph()
    except (Exception, APIException):
        return None


def _is_library_package(pkg):
    """Library packages loaded for describe_node/add_node count as user packages too."""
    lib = os.path.normcase(os.path.join(_APP.getPath(SDApplicationPath.DefaultResourcesDir), 'packages'))
    return os.path.normcase(os.path.dirname(pkg.getFilePath() or '')) == lib


def find_graph(identifier=None):
    """Compositing graph by identifier among the user's open packages (library packages
    excluded); default: the graph shown in the UI. A graph object is returned as is, so a batch
    keeps editing the graph it started on. Several open graphs with the same identifier (every
    new graph is "New_Graph") are ambiguous unless one of them is open in the UI."""
    if isinstance(identifier, SDSBSCompGraph):
        return identifier
    current = _current_graph()
    if not identifier:
        if current is None:
            raise RuntimeError('No graph identifier given and no graph is open in the UI.')
        if not isinstance(current, SDSBSCompGraph):
            raise RuntimeError('The graph open in the UI (%s) is not a compositing graph; pass graph=<id>.'
                               % current.getIdentifier())
        return current
    matches = [r for p in _PM.getUserPackages() if not _is_library_package(p)
               for r in p.getChildrenResources(True)
               if r.getIdentifier() == identifier and isinstance(r, SDSBSCompGraph)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise RuntimeError('Graph %r not found in open user packages.' % identifier)
    for g in matches:
        if current is not None and g.getIdentifier() == current.getIdentifier() \
                and g.getPackage().getUID() == current.getPackage().getUID():
            return g
    raise RuntimeError('%d open graphs are named %r (packages: %s); open the one you mean in Designer '
                       'or close the others.' % (len(matches), identifier, ', '.join(
                           g.getPackage().getFilePath() or 'never saved' for g in matches)))


def fmt(value):
    """Compact, printable form of an SDValue."""
    if value is None:
        return None
    try:
        x = value.get()
    except (Exception, APIException):
        return '<%s>' % type(value).__name__
    for attrs in (('x', 'y', 'z', 'w'), ('r', 'g', 'b', 'a')):
        if hasattr(x, attrs[0]):
            vals = tuple(getattr(x, a) for a in attrs if hasattr(x, a))
            return tuple(round(v, 4) if isinstance(v, float) else v for v in vals)
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, (bool, int, str)):
        return x
    return '<%s>' % type(x).__name__


def node_kind(node):
    ref = node.getReferencedResource()
    if ref is not None:
        return 'instance:' + ref.getIdentifier()
    return node.getDefinition().getId().replace('sbs::compositing::', '')


def _other_end(connection):
    # getPropertyConnections(prop) reports the queried side as "Output" and the
    # other node as "Input", whatever the data-flow direction.
    return connection.getInputPropertyNode(), connection.getInputProperty()


def describe_graph(identifier=None, node_ids=None, include_params=False, limit=400):
    g = find_graph(identifier)
    nodes = list(g.getNodes())
    print('graph %s: %d nodes' % (g.getIdentifier(), len(nodes)))
    try:
        size = g.getInputPropertyValueFromId('$outputsize').get()
        print('$outputsize (log2): %d x %d' % (size.x, size.y))
    except (Exception, APIException):
        pass
    try:
        frames, comments = graph_objects_summary(g)
        if frames or comments:
            print('frames: %s | comments: %d' % (', '.join(repr(f) for f in frames) or '-', comments))
    except (Exception, APIException):
        pass
    if node_ids:
        wanted = set(str(i) for i in node_ids)
        nodes = [n for n in nodes if n.getIdentifier() in wanted]
    for n in nodes[:limit]:
        pos = n.getPosition()
        line = '%s %s @(%d,%d)' % (n.getIdentifier(), node_kind(n), pos.x, pos.y)
        links = []
        for prop in n.getProperties(SDPropertyCategory.Input):
            if not prop.isConnectable():
                continue
            for c in n.getPropertyConnections(prop):
                other, other_prop = _other_end(c)
                links.append('%s<-%s.%s' % (prop.getId(), other.getIdentifier(), other_prop.getId()))
        if links:
            line += '  in: ' + ', '.join(links)
        print(line)
        if include_params:
            for prop in n.getProperties(SDPropertyCategory.Input):
                if prop.isConnectable():
                    continue
                cur = fmt(n.getPropertyValue(prop))
                default = fmt(prop.getDefaultValue())
                if cur != default and not (prop.getId() in ('$outputsize', '$pixelsize') and cur in ((0, 0), (1.0, 1.0))):
                    print('    %s = %r' % (prop.getId(), cur))
    if len(nodes) > limit:
        print('... %d more nodes (raise limit or filter node_ids)' % (len(nodes) - limit))


def _library_path(name):
    pkg_dir = os.path.join(_APP.getPath(SDApplicationPath.DefaultResourcesDir), 'packages')
    file_name, _, graph_id = name.partition('/')
    if not file_name.endswith('.sbs'):
        file_name += '.sbs'
    return os.path.join(pkg_dir, file_name), graph_id or os.path.splitext(file_name)[0]


def _load_library(path):
    for p in _PM.getPackages():
        if os.path.normpath(p.getFilePath() or '') == os.path.normpath(path):
            return p
    return _PM.loadUserPackage(path)


def _slider_range(node, prop_id):
    """'range a..b step c' from a library graph's input annotations ('' for atomic nodes,
    whose ranges the API doesn't expose)."""
    ref = node.getReferencedResource()
    if ref is None or prop_id.startswith('$'):
        return ''
    try:
        rprop = ref.getPropertyFromId(prop_id, SDPropertyCategory.Input)
        if rprop is None:
            return ''
        values = {}
        for key in ('min', 'max', 'step', 'clamp'):
            v = ref.getPropertyAnnotationValueFromId(rprop, key)
            values[key] = fmt(v) if v is not None else None
    except (Exception, APIException):
        return ''
    if values['min'] is None and values['max'] is None:
        return ''
    text = 'range %s..%s' % (values['min'], values['max'])
    if values['step'] not in (None, 0):
        text += ' step %s' % (round(values['step'], 4) if isinstance(values['step'], float) else values['step'])
    if values['clamp']:
        text += ' (clamped)'
    return text


def _short_description(prop):
    import re
    try:
        desc = prop.getDescription() or ''
    except (Exception, APIException):
        return ''
    desc = re.sub(r'<[^>]+>', '', desc).strip()
    return (desc[:157] + '...') if len(desc) > 160 else desc


def describe_node(definition):
    """definition: atomic name ('levels' or 'sbs::compositing::levels') or library
    '<package file>[/<graph id>]' (e.g. 'tile_generator', 'hbao.sbs/hbao')."""
    tmp = _PM.newUserPackage()
    try:
        g = SDSBSCompGraph.sNew(tmp)
        atomic_id = definition if definition.startswith('sbs::') else 'sbs::compositing::' + definition
        node = g.newNode(atomic_id) if atomic_id in atomic_definition_ids(g) else None
        if node is None:
            path, graph_id = _library_path(definition)
            if not os.path.exists(path):
                raise RuntimeError('%r is neither an atomic node nor a library package (%s)' % (definition, path))
            res = _load_library(path).findResourceFromUrl(graph_id)
            if res is None:
                raise RuntimeError('graph %r not found in %s' % (graph_id, path))
            node = g.newInstanceNode(res)
            print('library node %s (%s)' % (graph_id, os.path.basename(path)))
        else:
            print('atomic node %s' % atomic_id)
        print('output connector ids:', [p.getId() for p in node.getProperties(SDPropertyCategory.Output)])
        print('inputs:')
        for prop in node.getProperties(SDPropertyCategory.Input):
            ptype = prop.getType()
            kind = 'CONNECTOR' if prop.isConnectable() else ptype.getId()
            line = '  %-28s %-26s' % (prop.getId(), kind)
            label = prop.getLabel()
            if label and label != prop.getId():
                line += ' "%s"' % label
            if not prop.isConnectable():
                line += ' default=%r' % (fmt(node.getPropertyValue(prop)),)
                slider = _slider_range(node, prop.getId())
                if slider:
                    line += ' ' + slider
            print(line)
            desc = _short_description(prop)
            if desc:
                print('      ' + desc)
            if isinstance(ptype, SDTypeEnum):
                print('      enum: ' + ', '.join('%s=%s' % (e.getId(), fmt(e.getDefaultValue()))
                                               for e in ptype.getEnumerators()))
    finally:
        _PM.unloadUserPackage(tmp)


def _with_node_texture(g, node, output, use):
    """Compute the graph and call use(texture, output_property) for one node output. Designer
    only computes nodes that feed an output node, so a temporary output node is attached when
    needed and removed afterwards."""
    outs = list(node.getProperties(SDPropertyCategory.Output))
    if output:
        outs = [p for p in outs if p.getId() == output]
    if not outs:
        raise RuntimeError('output %r not found; outputs: %s' % (
            output, [p.getId() for p in node.getProperties(SDPropertyCategory.Output)]))
    g.compute()
    value = node.getPropertyValue(outs[0])
    texture = value.get() if value is not None else None
    temp_output = None
    try:
        if texture is None:
            temp_output = g.newNode('sbs::compositing::output')
            node.newPropertyConnectionFromId(outs[0].getId(), temp_output, 'inputNodeOutput')
            g.compute()
            value = node.getPropertyValue(outs[0])
            texture = value.get() if value is not None else None
        if texture is None:
            raise RuntimeError('node %s produced no texture (are its inputs connected?)' % node.getIdentifier())
        return use(texture, outs[0])
    finally:
        if temp_output is not None:
            g.deleteNode(temp_output)


def save_node_output(node_id, out_path, identifier=None, output=None):
    g = find_graph(identifier)
    node = _target(g, node_id)

    def use(texture, prop):
        texture.save(out_path)
        size = texture.getSize()
        print('%s %s.%s %dx%d %s' % (node_id, node_kind(node), prop.getId(), size.x, size.y,
                                     texture.getPixelFormat()))
    _with_node_texture(g, node, output, use)


def dump_node_pixels(node_id, out_path, identifier=None, output=None):
    """Write the node's raw pixel buffer to out_path and print its layout as JSON (for node_stats)."""
    import ctypes
    import json
    g = find_graph(identifier)
    node = _target(g, node_id)

    def use(texture, prop):
        size = texture.getSize()
        pitch = texture.getRowPitch()
        with open(out_path, 'wb') as f:
            f.write(ctypes.string_at(texture.getPixelBufferAddress(), pitch * size.y))
        print('PIXELS=' + json.dumps({'width': size.x, 'height': size.y, 'pitch': pitch,
                                      'bpp': texture.getBytesPerPixel(),
                                      'format': str(texture.getPixelFormat()).split('.')[-1],
                                      'node': '%s %s.%s' % (node_id, node_kind(node), prop.getId())}))
    _with_node_texture(g, node, output, use)


# ---------------------------------------------------------------- screenshots
PANELS = ('window', 'graph', '2d', '3d', 'explorer', 'parameters', 'library', 'console')
# Dock titles change with content ("dwarf_trimsheet", "Blend"), but their object names are stable
_PANEL_AREAS = {'explorer': 'areaA_', 'graph': 'areaB_', 'parameters': 'areaC_', '3d': 'areaD_',
                '2d': 'areaE_', 'console': 'areaF_', 'library': 'areaG_'}


def _visible_dock(mw, prefix):
    from PySide6 import QtWidgets
    for d in mw.findChildren(QtWidgets.QDockWidget):
        if d.objectName().startswith(prefix) and d.isVisible():
            return d
    return None


def _save_3d_render(mw, out_path):
    """The 3D view is GPU-drawn, so QWidget.grab() returns black. Use the view's own
    Camera > 'Copy Render to Clipboard' (the renderer's image, never screen pixels) and put
    the user's clipboard back afterwards."""
    import time
    from PySide6 import QtCore, QtWidgets
    app = QtWidgets.QApplication.instance()
    dock = _visible_dock(mw, _PANEL_AREAS['3d'])
    if dock is None:
        raise RuntimeError('the 3D View panel is not visible in Designer' + (
            " (it's showing its Home screen; open_graph closes it)" if _home_screen() is not None else ''))
    bars = dock.findChildren(QtWidgets.QMenuBar)
    if not bars:
        raise RuntimeError('3D View menu bar not found')
    # Keep Python references alive: Designer rebuilds these menus and stale wrappers raise
    keep, copy_action = [], None
    for top in list(bars[0].actions()):
        if top.text().replace('&', '') != 'Camera':
            continue
        menu = top.menu()
        keep += [top, menu]
        menu.aboutToShow.emit()  # menus are populated lazily
        app.processEvents()
        for action in menu.actions():
            if action.text().replace('&', '') == 'Copy Render to Clipboard':
                copy_action = action
                keep.append(action)
    if copy_action is None:
        raise RuntimeError("3D View has no 'Camera > Copy Render to Clipboard' action")

    clipboard = app.clipboard()
    original = clipboard.mimeData()
    backup = QtCore.QMimeData()
    for fmt in original.formats():
        backup.setData(fmt, original.data(fmt))
    try:
        clipboard.clear()
        copy_action.trigger()
        image = None
        for _ in range(100):
            app.processEvents()
            image = clipboard.image()
            if not image.isNull():
                break
            time.sleep(0.05)
        if image is None or image.isNull():
            raise RuntimeError('the 3D view did not produce a render (is a material shown?)')
        if not image.save(out_path):
            raise RuntimeError('could not save the 3D render')
        return image.width(), image.height()
    finally:
        clipboard.setMimeData(backup)
        app.processEvents()


def _graph_view(mw):
    """The graph editor's node view (a QGraphicsView in the graph dock; its scene coordinates
    are graph units), or None. The dock's title bar and toolbars are not part of it. The
    caller keeps `mw` (the main window) referenced while using the view, or PySide reports
    its wrappers as already deleted."""
    from PySide6 import QtWidgets
    dock = _visible_dock(mw, _PANEL_AREAS['graph'])
    if dock is None:
        return None
    views = [v for v in dock.findChildren(QtWidgets.QGraphicsView) if v.isVisible()]
    return max(views, key=lambda v: v.width() * v.height()) if views else None


def save_screenshot(panel, out_path):
    """Render one of Designer's own widgets to PNG with QWidget.grab(), or the 3D view via its
    own render. Screen/window grabs are deliberately not used: on macOS they copy whatever
    covers Designer, i.e. other apps. 'graph' is the node view alone, without the dock's
    title bar and toolbars."""
    from PySide6 import QtWidgets
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    if panel == '3d':
        width, height = _save_3d_render(mw, out_path)
        print('3d render %dx%d (clipboard restored)' % (width, height))
        return
    if panel == 'window':
        widget = mw
    else:
        prefix = _PANEL_AREAS.get(panel)
        if prefix is None:
            raise RuntimeError('unknown panel %r; use one of %s' % (panel, ', '.join(PANELS)))
        docks = [d for d in mw.findChildren(QtWidgets.QDockWidget)
                 if d.objectName().startswith(prefix) and d.isVisible()]
        if not docks:
            if _home_screen() is not None:
                raise RuntimeError('Designer is showing its Home screen, which hides the panels; '
                                   'open_graph closes it')
            raise RuntimeError('panel %r is not visible in Designer (open it via the Windows menu)' % panel)
        widget = docks[0]
        if panel == 'graph':
            widget = _graph_view(mw) or widget
    QtWidgets.QApplication.instance().processEvents()
    pixmap = widget.grab()
    if not pixmap.save(out_path):
        raise RuntimeError('could not save screenshot')
    current = _APP.getQtForPythonUIMgr().getCurrentGraph()
    print('%s %dx%d | graph in editor: %s' % (panel, pixmap.width(), pixmap.height(),
                                              current.getIdentifier() if current else None))


# ---------------------------------------------------------------- save / export
def _package_of(identifier):
    if not identifier:
        g = find_graph(None)
        return g.getPackage(), g
    for p in _PM.getUserPackages():
        if os.path.normpath(p.getFilePath() or '') == os.path.normpath(os.path.expanduser(identifier)):
            return p, None
    g = find_graph(identifier)
    return g.getPackage(), g


def save_package(identifier=None, path=None):
    """identifier: a graph identifier or a package file path (default: graph open in the UI)."""
    pkg, _ = _package_of(identifier)
    if path:
        path = os.path.abspath(os.path.expanduser(path))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _PM.savePackageAs(pkg, path)
        print('saved package as', path)
    else:
        if not pkg.getFilePath():
            raise RuntimeError('package was never saved; pass a path')
        _PM.savePackage(pkg)
        print('saved', pkg.getFilePath())


def export_outputs(identifier, out_dir, names=None, ext='png'):
    """Compute the graph in Designer and save each output node's texture as <identifier>.<ext>."""
    from sd.api.sdvaluestring import SDValueString
    g = find_graph(identifier)
    out_dir = os.path.abspath(os.path.expanduser(out_dir))
    os.makedirs(out_dir, exist_ok=True)
    g.compute()
    saved = []
    for i, node in enumerate(g.getOutputNodes()):
        try:
            ident = node.getAnnotationPropertyValueFromId('identifier').get()
        except (Exception, APIException):
            ident = 'output_%d' % i
        if names and ident not in names:
            continue
        for prop in node.getProperties(SDPropertyCategory.Output):
            value = node.getPropertyValue(prop)
            texture = value.get() if value is not None else None
            if texture is None:
                continue
            path = os.path.join(out_dir, '%s.%s' % (ident, ext))
            texture.save(path)
            size = texture.getSize()
            saved.append('%s  %dx%d %s' % (os.path.basename(path), size.x, size.y, texture.getPixelFormat()))
    if not saved:
        raise RuntimeError('no outputs exported (names %r)' % (names,))
    print('exported %d file(s) to %s:' % (len(saved), out_dir))
    print('\n'.join(saved))


# ---------------------------------------------------------------- quick edits
def _target(g, node_id):
    """'graph' (or empty) addresses the graph's own parameters, e.g. $outputsize."""
    if node_id in (None, '', 'graph'):
        return g
    node = g.getNodeFromId(str(node_id))
    if node is None:
        raise RuntimeError('node %s not found in graph %s' % (node_id, g.getIdentifier()))
    return node


def _make_value(prop, value):
    """Build the SDValue matching the property's type from a plain Python value."""
    from sd.api.sdbasetypes import float2, float3, float4, int2, int3, int4, ColorRGBA
    from sd.api.sdvaluebool import SDValueBool
    from sd.api.sdvaluecolorrgba import SDValueColorRGBA
    from sd.api.sdvaluefloat import SDValueFloat
    from sd.api.sdvaluefloat2 import SDValueFloat2
    from sd.api.sdvaluefloat3 import SDValueFloat3
    from sd.api.sdvaluefloat4 import SDValueFloat4
    from sd.api.sdvalueint import SDValueInt
    from sd.api.sdvalueint2 import SDValueInt2
    from sd.api.sdvalueint3 import SDValueInt3
    from sd.api.sdvalueint4 import SDValueInt4
    from sd.api.sdvaluestring import SDValueString
    ptype = prop.getType()
    if isinstance(ptype, SDTypeEnum):
        options = [(e.getId(), e.getDefaultValue()) for e in ptype.getEnumerators()]
        for eid, ev in options:
            if value == eid or (not isinstance(value, bool) and value == ev.get()):
                return ev
        raise RuntimeError('%s: %r is not one of %s' % (prop.getId(), value,
                           ', '.join('%s=%s' % (eid, ev.get()) for eid, ev in options)))
    tid = ptype.getId()
    seq = list(value) if isinstance(value, (list, tuple)) else None
    def as_bool(v):
        if isinstance(v, str):
            if v.strip().lower() not in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
                raise RuntimeError('%s expects true or false, got %r' % (prop.getId(), v))
            return v.strip().lower() in ('true', '1', 'yes', 'on')
        return bool(v)

    def as_int(v):
        if isinstance(v, float) and not v.is_integer():
            raise RuntimeError('%s is an integer parameter; %r is not a whole number' % (prop.getId(), v))
        return int(v)
    builders = {
        'bool': lambda: SDValueBool.sNew(as_bool(value)),
        'int': lambda: SDValueInt.sNew(as_int(value)),
        'float': lambda: SDValueFloat.sNew(float(value)),
        'string': lambda: SDValueString.sNew(str(value)),
        'float2': lambda: SDValueFloat2.sNew(float2(*map(float, seq))),
        'float3': lambda: SDValueFloat3.sNew(float3(*map(float, seq))),
        'float4': lambda: SDValueFloat4.sNew(float4(*map(float, seq))),
        'int2': lambda: SDValueInt2.sNew(int2(*map(as_int, seq))),
        'int3': lambda: SDValueInt3.sNew(int3(*map(as_int, seq))),
        'int4': lambda: SDValueInt4.sNew(int4(*map(as_int, seq))),
        'ColorRGBA': lambda: SDValueColorRGBA.sNew(ColorRGBA(*map(float, (seq + [1.0])[:4]))),
    }
    if tid not in builders:
        raise RuntimeError('%s: unsupported parameter type %s' % (prop.getId(), tid))
    if tid[-1].isdigit() and (seq is None or len(seq) != int(tid[-1])):
        raise RuntimeError('%s expects %s values' % (prop.getId(), tid[-1]))
    if tid == 'ColorRGBA' and (seq is None or len(seq) not in (3, 4)):
        raise RuntimeError('%s expects a colour [r, g, b] or [r, g, b, a]' % prop.getId())
    return builders[tid]()


def set_params(graph_id, node_id, params):
    from sd.api.sdproperty import SDPropertyInheritanceMethod
    g = find_graph(graph_id)
    target = _target(g, node_id)
    for pid, value in params.items():
        prop = target.getPropertyFromId(pid, SDPropertyCategory.Input)
        if prop is None:
            raise RuntimeError('no parameter %r on %s; see describe_node' % (pid, node_id or 'graph'))
        if prop.isConnectable():
            raise RuntimeError('%r is an input connector; use connect' % pid)
        before = fmt(target.getPropertyValue(prop))
        new_value = _make_value(prop, value)   # validate before changing anything
        if pid.startswith('$') and hasattr(target, 'setPropertyInheritanceMethod'):
            # $outputsize/$format etc. only take effect when not inherited
            try:
                target.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
            except (Exception, APIException):
                pass
        target.setPropertyValue(prop, new_value)
        print('%s.%s: %r -> %r' % (node_id or 'graph', pid, before, fmt(target.getPropertyValue(prop))))


def atomic_definition_ids(g):
    return {d.getId() for d in g.getNodeDefinitions()}


def _resolve_definition(g, definition):
    atomic_id = definition if definition.startswith('sbs::') else 'sbs::compositing::' + definition
    # Validate first: newNode() with an unknown id can hang Designer 15
    if atomic_id in atomic_definition_ids(g):
        return g.newNode(atomic_id)
    path, graph_id = _library_path(definition)
    if not os.path.exists(path):
        raise RuntimeError('%r is neither an atomic node nor a library package (%s)' % (definition, path))
    res = _load_library(path).findResourceFromUrl(graph_id)
    if res is None:
        raise RuntimeError('graph %r not found in %s' % (graph_id, path))
    return g.newInstanceNode(res)


def _place(node, position, existing):
    from sd.api.sdbasetypes import float2
    if position is None:
        # to the right of everything, so it doesn't land on top of existing nodes
        xs = [n.getPosition().x for n in existing] or [0.0]
        ys = [n.getPosition().y for n in existing] or [0.0]
        position = (max(xs) + 200.0, sum(ys) / len(ys))
    node.setPosition(float2(float(position[0]), float(position[1])))
    return position


def add_node(graph_id, definition, position=None, params=None):
    g = find_graph(graph_id)
    existing = list(g.getNodes())
    node = _resolve_definition(g, definition)
    position = _place(node, position, existing)
    print('added %s %s @(%d,%d)' % (node.getIdentifier(), node_kind(node), position[0], position[1]))
    print('outputs:', [p.getId() for p in node.getProperties(SDPropertyCategory.Output)])
    if params:
        set_params(graph_id, node.getIdentifier(), params)
    return node.getIdentifier()


def connect(graph_id, from_node, to_node, to_input, from_output=None):
    g = find_graph(graph_id)
    src, dst = _target(g, from_node), _target(g, to_node)
    outs = [p.getId() for p in src.getProperties(SDPropertyCategory.Output)]
    out_id = from_output or (outs[0] if outs else None)
    if out_id not in outs:
        raise RuntimeError('output %r not on node %s; outputs: %s' % (out_id, from_node, outs))
    ins = [p.getId() for p in dst.getProperties(SDPropertyCategory.Input) if p.isConnectable()]
    if to_input not in ins:
        raise RuntimeError('input %r not on node %s; connectors: %s' % (to_input, to_node, ins))
    src.newPropertyConnectionFromId(out_id, dst, to_input)
    print('connected %s.%s -> %s.%s' % (from_node, out_id, to_node, to_input))


def disconnect(graph_id, node_id, input_id):
    g = find_graph(graph_id)
    node = _target(g, node_id)
    prop = node.getPropertyFromId(input_id, SDPropertyCategory.Input)
    if prop is None or not prop.isConnectable():
        raise RuntimeError('%r is not an input connector on node %s' % (input_id, node_id))
    count = len(node.getPropertyConnections(prop))
    node.deletePropertyConnections(prop)
    print('removed %d connection(s) into %s.%s' % (count, node_id, input_id))


def delete_nodes(graph_id, node_ids):
    g = find_graph(graph_id)
    for nid in node_ids:
        node = _target(g, nid)
        kind = node_kind(node)
        g.deleteNode(node)
        print('deleted %s %s' % (nid, kind))


def import_bitmap(graph_id, path, embed='link', position=None, name=None):
    """Bitmap node for an image file. embed: 'link' (reference the file where it is) or 'copy'
    (copy into <package>.resources/, or a temp folder until the package is saved).
    Embedding into the .sbs itself isn't supported by the API (NotSupported)."""
    from sd.api.sdresource import EmbedMethod
    from sd.api.sdresourcebitmap import SDResourceBitmap
    methods = {'link': EmbedMethod.Linked, 'copy': EmbedMethod.CopiedAndLinked}
    if embed not in methods:
        raise RuntimeError('embed must be one of %s' % ', '.join(methods))
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(path):
        raise RuntimeError('no such file: %s' % path)
    g = find_graph(graph_id)
    pkg = g.getPackage()
    existing = list(g.getNodes())
    res = None
    if embed == 'link' and not name:
        # reuse a resource that already links this file instead of adding probe_1, probe_2...
        for r in pkg.getChildrenResources(True):
            if (isinstance(r, SDResourceBitmap) and r.getEmbedMethod() == EmbedMethod.Linked
                    and os.path.normpath(r.getFilePath() or '') == path):
                res = r
                print('reusing bitmap resource', r.getIdentifier())
                break
    if res is None:
        res = SDResourceBitmap.sNewFromFile(pkg, path, methods[embed])
        if res is None:
            raise RuntimeError('Designer could not load %s as a bitmap' % path)
        if name:
            res.setIdentifier(name)
        print('bitmap resource %s (%s): %s' % (res.getIdentifier(), embed, res.getFilePath()))
    node = g.newInstanceNode(res)
    position = _place(node, position, existing)
    size = fmt(node.getPropertyValue(node.getPropertyFromId('$outputsize', SDPropertyCategory.Input)))
    print('added %s bitmap @(%d,%d), size %s (log2, the image\'s own; set $outputsize to change)'
          % (node.getIdentifier(), position[0], position[1], size))
    print('outputs:', [p.getId() for p in node.getProperties(SDPropertyCategory.Output)])
    return node.getIdentifier()


def quit_designer(discard_unsaved=False):
    """Close Designer's main window shortly after this call returns. Refuses while user packages
    have unsaved changes, unless discard_unsaved (then those packages are unloaded first, so
    Designer doesn't stop at a save prompt)."""
    from PySide6.QtCore import QTimer
    modified = [p for p in _PM.getUserPackages() if p.isModified()]
    if modified and not discard_unsaved:
        raise RuntimeError('unsaved changes in %d package(s): %s. Save them (save_package) or pass '
                           'discard_unsaved=True.' % (len(modified), '; '.join(
                               '%s [%s]' % (p.getFilePath() or 'never saved', ', '.join(
                                   r.getIdentifier() for r in p.getChildrenResources(False)))
                               for p in modified)))
    for p in modified:
        print('discarding unsaved changes:', p.getFilePath() or 'never-saved package')
        _PM.unloadUserPackage(p)
    from PySide6.QtWidgets import QApplication
    qt_app = QApplication.instance()
    # getMainWindow() is a hidden QMainWindow; the window the user sees is another top-level
    # widget. Close the visible ones (Designer's normal shutdown). Fallback: exit(), which stops
    # the event loops; quit() would not, as Qt 6 cancels it when a window refuses to close.
    # Deferred, so the bridge can still send this reply.
    QTimer.singleShot(300, lambda: [w.close() for w in qt_app.topLevelWidgets() if w.isVisible()])
    QTimer.singleShot(5000, lambda: qt_app.exit(0))
    print('closing Designer')


# ---------------------------------------------------------------- editor / graphs
def _process_events(n=10):
    from PySide6 import QtWidgets
    for _ in range(n):
        QtWidgets.QApplication.instance().processEvents()


def _fit_graph_view():
    """Trigger the graph view's own 'Fit in view (selection)' (F); with nothing selected it fits
    the whole graph. Returns False if the action can't be found."""
    from PySide6 import QtWidgets
    mw = _APP.getQtForPythonUIMgr().getMainWindow()
    dock = _visible_dock(mw, _PANEL_AREAS['graph'])
    if dock is None:
        return False
    for bar in dock.findChildren(QtWidgets.QToolBar):
        for action in bar.actions():
            if action.text() == 'Fit in view (selection)':
                action.trigger()
                _process_events()
                return True
    return False


def _home_screen():
    """Designer's window is a stack: the main window (panels) and the Home screen. While Home
    is showing, every panel counts as invisible. Returns (stack, home page, its 'Close home
    screen' button), or None. Keep all three referenced while using the button, or PySide
    reports it as already deleted."""
    from PySide6 import QtWidgets
    for top in QtWidgets.QApplication.instance().topLevelWidgets():
        if isinstance(top, QtWidgets.QStackedWidget) and top.isVisible():
            page = top.currentWidget()
            for button in (page.findChildren(QtWidgets.QAbstractButton) if page is not None else []):
                if button.objectName() == 'close_btn':
                    return top, page, button
    return None


def leave_home_screen():
    home = _home_screen()
    if home is None:
        return
    stack, page, button = home
    button.click()  # Designer's own "Close home screen"
    _process_events()
    if stack.currentWidget() is page:
        raise RuntimeError("could not close Designer's Home screen")
    print('closed the Home screen')


def _fit_area(g, node_ids=None, frame=None, rect=None):
    """(x, y, w, h) in graph units: a frame (by title), the nodes' bounding box, or rect."""
    if frame is not None:
        from sd.api.sdgraphobjectframe import SDGraphObjectFrame
        frames = [o for o in g.getGraphObjects() if isinstance(o, SDGraphObjectFrame)]
        found = [f for f in frames if f.getTitle() == frame] or \
                [f for f in frames if f.getTitle().lower() == str(frame).lower()]
        if len(found) != 1:
            raise RuntimeError('%s frame titled %r; frames: %s' % (
                'more than one' if found else 'no', frame, ', '.join(repr(f.getTitle()) for f in frames) or 'none'))
        pos, size = found[0].getPosition(), found[0].getSize()
        return pos.x, pos.y, size.x, size.y, 'frame %r' % found[0].getTitle()
    if node_ids:
        nodes = [_target(g, i) for i in node_ids]
        xs = [n.getPosition().x for n in nodes]
        ys = [n.getPosition().y for n in nodes]
        half = _NODE_SIZE / 2.0
        return (min(xs) - half, min(ys) - half, max(xs) - min(xs) + _NODE_SIZE, max(ys) - min(ys) + _NODE_SIZE,
                '%d node(s)' % len(nodes))
    x, y, w, h = (float(v) for v in rect)
    if w <= 0 or h <= 0:
        raise RuntimeError('rect is [x, y, width, height] with a positive width and height')
    return x, y, w, h, 'rect'


FIT_MAX_ZOOM = 1.0   # 100 %: a node at its normal size, never larger
FIT_PADDING = 0.05   # of the fitted area, on every side


def _fit_view_to(g, node_ids=None, frame=None, rect=None):
    from PySide6.QtCore import QRectF, Qt
    x, y, w, h, what = _fit_area(g, node_ids, frame, rect)
    mw = _APP.getQtForPythonUIMgr().getMainWindow()   # keeps the view's wrappers alive
    view = _graph_view(mw)
    if view is None:
        raise RuntimeError('the graph view is not visible in Designer')
    pad = max(w, h) * FIT_PADDING + 20.0
    area = QRectF(x - pad, y - pad, w + 2 * pad, h + 2 * pad)
    view.fitInView(area, Qt.KeepAspectRatio)
    if view.transform().m11() > FIT_MAX_ZOOM:
        view.resetTransform()
        view.scale(FIT_MAX_ZOOM, FIT_MAX_ZOOM)
        view.centerOn(area.center())
    _process_events()
    seen = view.mapToScene(view.viewport().rect()).boundingRect()
    print('fitted %s: zoom %d%%, visible %d,%d to %d,%d' % (
        what, round(view.transform().m11() * 100), seen.left(), seen.top(), seen.right(), seen.bottom()))


def open_graph(identifier, node_id=None, node_ids=None, frame=None, rect=None):
    """Open a graph in Designer's graph editor; fit the view to a frame, nodes or a rectangle,
    or centre it on one node; by default fit the whole graph."""
    g = find_graph(identifier)
    leave_home_screen()  # otherwise the graph opens behind it
    ui = _APP.getUIMgr()
    ui.openResourceInEditor(g)
    _process_events()
    print('opened', g.getIdentifier())
    if node_ids or frame is not None or rect is not None:
        _fit_view_to(g, node_ids, frame, rect)
        return
    if not node_id:
        if _fit_graph_view():
            print('fitted the whole graph in view')
    if node_id:
        node = _target(g, node_id)
        views = [ui.getGraphViewIDAt(i) for i in range(ui.getGraphViewIDCount())]
        views = [v for v in views if ui.getGraphFromGraphViewID(v) is not None
                 and ui.getGraphFromGraphViewID(v).getIdentifier() == g.getIdentifier()]
        if not views:
            raise RuntimeError('graph opened but no graph view shows it')
        ui.focusGraphNode(views[0], node)
        _process_events()
        print('focused node %s %s' % (node.getIdentifier(), node_kind(node)))


def create_graph(name, save_path=None, size_log2=11):
    """New package with one compositing graph (fixed output size 2^size_log2)."""
    from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
    from sd.api.sdbasetypes import int2
    from sd.api.sdproperty import SDPropertyInheritanceMethod
    from sd.api.sdvalueint2 import SDValueInt2
    pkg = _PM.newUserPackage()
    g = SDSBSCompGraph.sNew(pkg)
    g.setIdentifier(name)
    prop = g.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
    g.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
    g.setPropertyValue(prop, SDValueInt2.sNew(int2(size_log2, size_log2)))
    print('created graph %s (%d px)' % (name, 2 ** size_log2))
    if save_path:
        save_path = os.path.abspath(os.path.expanduser(save_path))
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        _PM.savePackageAs(pkg, save_path)
        print('saved package as', save_path)


def move_nodes(identifier, positions):
    from sd.api.sdbasetypes import float2
    g = find_graph(identifier)
    for nid, (x, y) in positions.items():
        _target(g, nid).setPosition(float2(float(x), float(y)))
        print('moved %s to (%d, %d)' % (nid, x, y))


def list_atomic():
    g = _current_graph()
    if not isinstance(g, SDSBSCompGraph):     # a function graph lists sbs::function::* instead
        g = None
    tmp = None
    if g is None:
        tmp = _PM.newUserPackage()
        g = SDSBSCompGraph.sNew(tmp)
    try:
        ids = sorted(d.getId() for d in g.getNodeDefinitions())
        print('RESOURCES_DIR=' + _APP.getPath(SDApplicationPath.DefaultResourcesDir))
        for i in ids:
            print('ATOMIC=' + i)
    finally:
        if tmp is not None:
            _PM.unloadUserPackage(tmp)


# ---------------------------------------------------------------- graph inputs (exposed params)
_GETTERS = {'float': 'get_float1', 'float2': 'get_float2', 'float3': 'get_float3', 'float4': 'get_float4',
            'ColorRGBA': 'get_float4', 'int': 'get_integer1', 'int2': 'get_integer2',
            'int3': 'get_integer3', 'int4': 'get_integer4', 'bool': 'get_bool', 'string': 'get_string'}


def _graph_inputs(g):
    return [p for p in g.getProperties(SDPropertyCategory.Input) if not p.getId().startswith('$')]


def _set_annotation(g, prop, key, value):
    from sd.api.sdvaluebool import SDValueBool
    from sd.api.sdvaluefloat import SDValueFloat
    from sd.api.sdvaluestring import SDValueString
    if isinstance(value, bool):
        v = SDValueBool.sNew(value)
    elif isinstance(value, (int, float)):
        v = SDValueFloat.sNew(float(value))
    else:
        v = SDValueString.sNew(str(value))
    g.setPropertyAnnotationValueFromId(prop, key, v)


def expose_param(identifier, node_id, param, input_id=None, label=None, default=None,
                 minimum=None, maximum=None, step=None, group=None):
    """Create a graph input with the parameter's own type and drive the parameter from it."""
    from sd.api.sdtypeint import SDTypeInt
    from sd.api.sdvaluestring import SDValueString
    g = find_graph(identifier)
    node = _target(g, node_id)
    prop = node.getPropertyFromId(param, SDPropertyCategory.Input)
    if prop is None or prop.isConnectable():
        raise RuntimeError('%r is not a parameter of node %s; see describe_node' % (param, node_id))
    ptype = prop.getType()
    is_enum = isinstance(ptype, SDTypeEnum)
    type_id = 'int' if is_enum else ptype.getId()
    getter = _GETTERS.get(type_id)
    if getter is None:
        raise RuntimeError('parameters of type %s cannot be exposed by this tool' % type_id)
    input_id = input_id or param
    if g.getPropertyFromId(input_id, SDPropertyCategory.Input) is not None:
        raise RuntimeError('graph already has an input %r; pick another input_id' % input_id)
    try:
        existing = node.getPropertyGraph(prop)
    except (Exception, APIException):
        existing = None
    if existing is not None and len(existing.getNodes()):
        raise RuntimeError('%s.%s is already driven by a function; replacing it would lose that logic. '
                           'Edit the function by hand, or remove its graph input first.' % (node_id, param))
    from sd.api.sdvalueint import SDValueInt
    value = _make_value(prop, default) if default is not None else node.getPropertyValue(prop)  # validate first
    if is_enum:
        value = SDValueInt.sNew(int(value.get()))
    inp = g.newProperty(input_id, SDTypeInt.sNew() if is_enum else ptype, SDPropertyCategory.Input)
    try:
        g.setPropertyValue(inp, value)
        _set_annotation(g, inp, 'label', label or input_id.replace('_', ' ').capitalize())
        for key, val in (('min', minimum), ('max', maximum), ('step', step), ('group', group)):
            if val is not None:
                _set_annotation(g, inp, key, val)
        fg = existing or node.newPropertyGraph(prop, 'SDSBSFunctionGraph')
        get = fg.newNode('sbs::function::' + getter)
        get.setInputPropertyValueFromId('__constant__', SDValueString.sNew(input_id))
        fg.setOutputNode(get, True)
    except (Exception, APIException):
        g.deleteProperty(inp)   # don't leave an input that drives nothing
        raise
    print('exposed %s.%s as graph input %r (%s, default %r)' % (
        node_id, param, input_id, type_id, fmt(g.getPropertyValue(inp))))


def _plain_binding(fg):
    """The input id if this function graph is exactly what expose_param builds (one get_* node),
    else None: a hand-written expression or a Pixel Processor function."""
    nodes = list(fg.getNodes())
    if len(nodes) == 1 and '::get_' in nodes[0].getDefinition().getId():
        return fmt(nodes[0].getInputPropertyValueFromId('__constant__'))
    return None


def _input_users(g, plain_only=False):
    """input id -> ['node.param', ...] for parameters whose function reads it (with plain_only,
    only those that are nothing but that read)."""
    users = {}
    for node in g.getNodes():
        for prop in node.getProperties(SDPropertyCategory.Input):
            if prop.isConnectable():
                continue
            try:
                fg = node.getPropertyGraph(prop)
            except (Exception, APIException):
                fg = None
            if fg is None:
                continue
            ref = '%s.%s' % (node.getIdentifier(), prop.getId())
            if plain_only:
                name = _plain_binding(fg)
                if name is not None:
                    users.setdefault(name, []).append(ref)
                continue
            for fnode in fg.getNodes():
                if '::get_' in fnode.getDefinition().getId():
                    users.setdefault(fmt(fnode.getInputPropertyValueFromId('__constant__')), []).append(ref)
    return users


def list_graph_inputs(identifier=None):
    g = find_graph(identifier)
    size_prop = g.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
    method = g.getPropertyInheritanceMethod(size_prop)
    if method == method.__class__.RelativeToParent:
        print('size: overridable, default %d px' % g.getDefaultParentSize().x)
    else:
        print('size: fixed, log2 %s' % (fmt(g.getPropertyValue(size_prop)),))
    users = _input_users(g)
    inputs = _graph_inputs(g)
    if not inputs:
        print('no exposed inputs')
    for inp in inputs:
        notes = []
        for key in ('label', 'min', 'max', 'step', 'group'):
            try:
                v = fmt(g.getPropertyAnnotationValueFromId(inp, key))
            except (Exception, APIException):
                v = None
            if v not in (None, ''):
                notes.append('%s=%r' % (key, v))
        print('%s (%s) = %r  %s  drives: %s' % (inp.getId(), inp.getType().getId(),
              fmt(g.getPropertyValue(inp)), ' '.join(notes), ', '.join(users.get(inp.getId(), [])) or '-'))


def remove_graph_input(identifier, input_id):
    """Delete a graph input; parameters bound to it (as expose_param does) keep its current
    value as a constant. Refuses while a larger function (an expression, a Pixel Processor) still
    reads it, since removing the input would break that function."""
    g = find_graph(identifier)
    inp = g.getPropertyFromId(input_id, SDPropertyCategory.Input)
    if inp is None or input_id.startswith('$'):
        raise RuntimeError('graph has no exposed input %r' % input_id)
    plain = _input_users(g, plain_only=True).get(input_id, [])
    other = [ref for ref in _input_users(g).get(input_id, []) if ref not in plain]
    if other:
        raise RuntimeError('input %r is read inside the functions of %s; edit those by hand first '
                           '(nothing was changed)' % (input_id, ', '.join(other)))
    value = g.getPropertyValue(inp)
    for ref in plain:
        nid, pid = ref.split('.', 1)
        node = g.getNodeFromId(nid)
        prop = node.getPropertyFromId(pid, SDPropertyCategory.Input)
        node.deletePropertyGraph(prop)
        try:
            node.setPropertyValue(prop, value)
        except (Exception, APIException):
            try:   # an int input bound to an enum parameter
                node.setPropertyValue(prop, _make_value(prop, fmt(value)))
            except (Exception, APIException) as e:
                print('WARNING: %s keeps its previous value; could not set %r (%s)' % (ref, fmt(value), e))
        print('unbound %s (kept value %r)' % (ref, fmt(node.getPropertyValue(prop))))
    g.deleteProperty(inp)
    print('removed graph input', input_id)


def set_graph_size(identifier, size_log2, overridable=True):
    """overridable: size follows the parent (render_sbs size_log2 / $outputsize can change it),
    with 2^size_log2 as default. Otherwise the size is fixed."""
    from sd.api.sdbasetypes import int2
    from sd.api.sdproperty import SDPropertyInheritanceMethod
    from sd.api.sdvalueint2 import SDValueInt2
    g = find_graph(identifier)
    prop = g.getPropertyFromId('$outputsize', SDPropertyCategory.Input)
    if overridable:
        g.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.RelativeToParent)
        g.setDefaultParentSize(int2(2 ** size_log2, 2 ** size_log2))
        g.setPropertyValue(prop, SDValueInt2.sNew(int2(0, 0)))
        print('size: overridable, default %d px' % g.getDefaultParentSize().x)
    else:
        g.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
        g.setPropertyValue(prop, SDValueInt2.sNew(int2(size_log2, size_log2)))
        print('size: fixed %d px' % 2 ** size_log2)


# ---------------------------------------------------------------- batch edits
def apply_edits(identifier, ops):
    """Run a list of edit operations in order. 'ref' names a node added earlier in the batch;
    node fields accept a ref, a node id, or 'graph'. Stops at the first failing op."""
    g = find_graph(identifier)
    gid = g      # the object, so every op edits this graph even if another has the same name
    refs = {}
    node = lambda value: refs.get(value, value)
    for i, op in enumerate(ops):
        kind = op.get('op')
        try:
            if kind == 'add':
                new_id = add_node(gid, op['definition'], op.get('position'), op.get('params'))
                if op.get('ref'):
                    refs[op['ref']] = new_id
                    print('  ref %r = %s' % (op['ref'], new_id))
            elif kind == 'bitmap':
                new_id = import_bitmap(gid, op['path'], op.get('embed', 'link'), op.get('position'),
                                       op.get('name'))
                if op.get('ref'):
                    refs[op['ref']] = new_id
                    print('  ref %r = %s' % (op['ref'], new_id))
            elif kind == 'set':
                set_params(gid, node(op['node']), op['params'])
            elif kind == 'connect':
                connect(gid, node(op['from']), node(op['to']), op['input'], op.get('output'))
            elif kind == 'disconnect':
                disconnect(gid, node(op['node']), op['input'])
            elif kind == 'move':
                move_nodes(gid, {node(op['node']): op['position']})
            elif kind == 'delete':
                delete_nodes(gid, [node(op['node'])])
            elif kind == 'expose':
                expose_param(gid, node(op['node']), op['param'], op.get('input_id'), op.get('label'),
                             op.get('default'), op.get('min'), op.get('max'), op.get('step'), op.get('group'))
            else:
                raise RuntimeError('unknown op %r (add, bitmap, set, connect, disconnect, move, delete, expose)' % kind)
        except (Exception, APIException) as e:
            done = 'ops 0-%d were applied' % (i - 1) if i else 'no earlier op was applied'
            raise RuntimeError('op %d (%s) failed: %s. %s%s; Ctrl+Z on this graph reverts the whole '
                               'batch.' % (i, kind, e, done, ' (its node was added before the failure)'
                                           if kind in ('add', 'bitmap') and refs.get(op.get('ref')) is None
                                           and op.get('params') else ''))
    print('applied %d op(s); refs: %s' % (len(ops), refs))


# ---------------------------------------------------------------- parameter sweep
def sweep_param(identifier, node_id, param, values, out_dir, view_node=None, output=None):
    """Set `param` on `node_id` (or graph input when node_id == 'graph') to each value, dump the
    raw pixels of `view_node` (default: the same node) per value, then restore the original."""
    import ctypes
    import json
    g = find_graph(identifier)
    target = _target(g, node_id)
    prop = target.getPropertyFromId(param, SDPropertyCategory.Input)
    if prop is None or prop.isConnectable():
        raise RuntimeError('%r is not a parameter of %s; see describe_node / list_graph_inputs'
                           % (param, node_id))
    if node_id not in (None, '', 'graph'):
        try:
            driven = target.getPropertyGraph(prop)
        except (Exception, APIException):
            driven = None
        if driven is not None:
            raise RuntimeError('%s.%s is driven by a graph input or function; sweep the graph input '
                               'instead (node_id="graph", param=<input id>, see list_graph_inputs)'
                               % (node_id, param))
    view = _target(g, view_node or node_id) if (view_node or node_id not in (None, '', 'graph')) else None
    if view is None:
        raise RuntimeError('sweeping a graph input needs view_node (the node to look at)')
    original = target.getPropertyValue(prop)
    original_text = fmt(original)
    inherit = None
    if param.startswith('$') and hasattr(target, 'getPropertyInheritanceMethod'):
        # like set_params: $outputsize/$format only take effect when not inherited
        from sd.api.sdproperty import SDPropertyInheritanceMethod
        inherit = target.getPropertyInheritanceMethod(prop)
        target.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
    try:
        for i, value in enumerate(values):
            target.setPropertyValue(prop, _make_value(prop, value))

            def use(texture, out_prop, i=i, value=value):
                size = texture.getSize()
                pitch = texture.getRowPitch()
                with open(os.path.join(out_dir, '%d.raw' % i), 'wb') as f:
                    f.write(ctypes.string_at(texture.getPixelBufferAddress(), pitch * size.y))
                print('SWEEP=' + json.dumps({'index': i, 'value': fmt(target.getPropertyValue(prop)),
                                             'width': size.x, 'height': size.y, 'pitch': pitch,
                                             'bpp': texture.getBytesPerPixel(),
                                             'format': str(texture.getPixelFormat()).split('.')[-1]}))
            _with_node_texture(g, view, output, use)
    finally:
        target.setPropertyValue(prop, original)
        if inherit is not None:
            target.setPropertyInheritanceMethod(prop, inherit)
        print('restored %s.%s to %r' % (node_id or 'graph', param, original_text))


# ---------------------------------------------------------------- snapshots
def save_package_copy(identifier, path):
    """Write a copy of the graph's package to `path` without changing the package's own file
    path or saved state (saveCopyOfPackageAs)."""
    g = find_graph(identifier)
    pkg = g.getPackage()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _PM.saveCopyOfPackageAs(pkg, path)
    print('COPY=' + path)
    print('PACKAGE=' + (pkg.getFilePath() or ''))
    print('GRAPH=' + g.getIdentifier())


# ---------------------------------------------------------------- layout, frames, comments
_NODE_SIZE = 96.0   # graph-view size of a node; positions are node centres


def _links(g, nodes):
    """(upstream_id, downstream_id) pairs between the given nodes."""
    ids = {n.getIdentifier() for n in nodes}
    pairs = set()
    for n in nodes:
        for prop in n.getProperties(SDPropertyCategory.Input):
            if not prop.isConnectable():
                continue
            for c in n.getPropertyConnections(prop):
                other, _ = _other_end(c)
                if other.getIdentifier() in ids:
                    pairs.add((other.getIdentifier(), n.getIdentifier()))
    return pairs


def arrange_graph(identifier, node_ids=None, spacing=(200.0, 150.0)):
    """Layered left-to-right layout by data flow. Only positions change, never connections.
    With node_ids, only those nodes are arranged, starting at their current top-left corner."""
    from sd.api.sdbasetypes import float2
    g = find_graph(identifier)
    nodes = list(g.getNodes())
    if node_ids:
        wanted = {str(i) for i in node_ids}
        nodes = [n for n in nodes if n.getIdentifier() in wanted]
    if not nodes:
        raise RuntimeError('no nodes to arrange')
    by_id = {n.getIdentifier(): n for n in nodes}
    pairs = _links(g, nodes)
    preds = {i: [a for a, b in pairs if b == i] for i in by_id}
    succs = {i: [b for a, b in pairs if a == i] for i in by_id}
    # layer = longest path from a source (iterative, cycle-safe)
    layer = {i: 0 for i in by_id}
    for _ in range(len(by_id)):
        changed = False
        for a, b in pairs:
            if layer[b] < layer[a] + 1:
                layer[b] = layer[a] + 1
                changed = True
        if not changed:
            break
    # outputs go to the last column
    last = max(layer.values())
    for i, n in by_id.items():
        if n.getDefinition().getId() == 'sbs::compositing::output':
            layer[i] = last
    columns = {}
    for i in sorted(by_id, key=lambda i: (by_id[i].getPosition().y, by_id[i].getPosition().x)):
        columns.setdefault(layer[i], []).append(i)
    # barycentre ordering to reduce crossings: a few sweeps in both directions
    order = {i: k for col in columns.values() for k, i in enumerate(col)}
    for sweep in range(4):
        keys = sorted(columns) if sweep % 2 == 0 else sorted(columns, reverse=True)
        for L in keys:
            neigh = preds if sweep % 2 == 0 else succs
            def bary(i):
                ns = neigh[i]
                return sum(order[j] for j in ns) / len(ns) if ns else order[i]
            columns[L].sort(key=bary)
            for k, i in enumerate(columns[L]):
                order[i] = k
    xs = [n.getPosition().x for n in nodes]
    ys = [n.getPosition().y for n in nodes]
    x0, y0 = min(xs), min(ys)
    dx, dy = spacing
    tallest = max(len(c) for c in columns.values())
    for L, col in columns.items():
        top = y0 + (tallest - len(col)) * dy / 2.0     # centre each column vertically
        for k, i in enumerate(col):
            by_id[i].setPosition(float2(x0 + L * dx, top + k * dy))
    print('arranged %d node(s) into %d column(s), %d link(s); spacing %dx%d' % (
        len(nodes), len(columns), len(pairs), dx, dy))


def add_frame(identifier, node_ids, title, color=None, description=None, margin=40.0):
    from sd.api.sdbasetypes import float2, ColorRGBA
    from sd.api.sdgraphobjectframe import SDGraphObjectFrame
    g = find_graph(identifier)
    nodes = [_target(g, i) for i in node_ids]
    if not nodes:
        raise RuntimeError('add_frame needs at least one node')
    half = _NODE_SIZE / 2.0
    xs = [n.getPosition().x for n in nodes]
    ys = [n.getPosition().y for n in nodes]
    left, right = min(xs) - half - margin, max(xs) + half + margin
    top, bottom = min(ys) - half - margin - 30.0, max(ys) + half + margin   # room for the title bar
    frame = SDGraphObjectFrame.sNew(g)
    frame.setTitle(title)
    frame.setPosition(float2(left, top))
    frame.setSize(float2(right - left, bottom - top))
    if color:
        c = list(color) + [1.0] * (4 - len(color))
        frame.setColor(ColorRGBA(*map(float, c[:4])))
    if description:
        frame.setDescription(description)
    print('frame %r around %d node(s) at (%d, %d) size %dx%d' % (
        title, len(nodes), left, top, right - left, bottom - top))


def add_comment(identifier, text, node_id=None, position=None):
    from sd.api.sdbasetypes import float2
    from sd.api.sdgraphobjectcomment import SDGraphObjectComment
    g = find_graph(identifier)
    if node_id:
        comment = SDGraphObjectComment.sNewAsChild(_target(g, node_id))
    else:
        comment = SDGraphObjectComment.sNew(g)
        if position:
            comment.setPosition(float2(float(position[0]), float(position[1])))
    comment.setDescription(text)
    print('comment added' + (' on node %s' % node_id if node_id else ''))


def graph_objects_summary(g):
    from sd.api.sdgraphobjectframe import SDGraphObjectFrame
    from sd.api.sdgraphobjectcomment import SDGraphObjectComment
    frames, comments = [], 0
    for obj in g.getGraphObjects():
        if isinstance(obj, SDGraphObjectFrame):
            frames.append(obj.getTitle())
        elif isinstance(obj, SDGraphObjectComment):
            comments += 1
    return frames, comments


# ---------------------------------------------------------------- reload (for file-level edits)
def package_file_of(identifier, save=False):
    """Report the graph's package file (for edits the API can't make); with save, save it first."""
    g = find_graph(identifier)
    pkg = g.getPackage()
    path = pkg.getFilePath()
    if not path:
        raise RuntimeError('the package has never been saved; save it first (the save_package tool, save_as=...)')
    if save:
        _PM.savePackage(pkg)
    current = _APP.getQtForPythonUIMgr().getCurrentGraph()
    print('FILE=' + path)
    print('GRAPH=' + g.getIdentifier())
    print('OPEN=' + ('1' if current is not None and current.getIdentifier() == g.getIdentifier() else '0'))


def unload_package_file(path):
    """Close every open copy of the package at `path` (its graph views are torn down when this
    call returns to Designer's event loop; load it again in a separate call)."""
    norm = os.path.normpath(path)
    count = 0
    for p in list(_PM.getUserPackages()):
        if os.path.normpath(p.getFilePath() or '') == norm:
            _PM.unloadUserPackage(p)
            count += 1
    print('unloaded %d package(s): %s' % (count, path))


def load_package_file(path):
    _PM.loadUserPackage(path)
    print('loaded', path)