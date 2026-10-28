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


def find_graph(identifier=None):
    """Graph by identifier among open user packages; default: graph shown in the UI."""
    if not identifier:
        try:
            g = _APP.getQtForPythonUIMgr().getCurrentGraph()
        except (Exception, APIException):
            g = None
        if g is None:
            raise RuntimeError('No graph identifier given and no graph is open in the UI.')
        return g
    for p in _PM.getUserPackages():
        for r in p.getChildrenResources(True):
            if r.getIdentifier() == identifier and isinstance(r, SDSBSCompGraph):
                return r
    raise RuntimeError('Graph %r not found in open user packages.' % identifier)


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
            print(line)
            if isinstance(ptype, SDTypeEnum):
                print('      enum: ' + ', '.join('%s=%s' % (e.getId(), fmt(e.getDefaultValue()))
                                               for e in ptype.getEnumerators()))
    finally:
        _PM.unloadUserPackage(tmp)


def save_node_output(node_id, out_path, identifier=None, output=None):
    g = find_graph(identifier)
    node = g.getNodeFromId(str(node_id))
    if node is None:
        raise RuntimeError('node %s not found in graph %s' % (node_id, g.getIdentifier()))
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
            # Designer only computes nodes that feed an output node: attach a temporary one
            temp_output = g.newNode('sbs::compositing::output')
            node.newPropertyConnectionFromId(outs[0].getId(), temp_output, 'inputNodeOutput')
            g.compute()
            value = node.getPropertyValue(outs[0])
            texture = value.get() if value is not None else None
        if texture is None:
            raise RuntimeError('node %s produced no texture (are its inputs connected?)' % node_id)
        texture.save(out_path)
    finally:
        if temp_output is not None:
            g.deleteNode(temp_output)
    size = texture.getSize()
    print('%s %s.%s %dx%d %s' % (node_id, node_kind(node), outs[0].getId(), size.x, size.y,
                                 texture.getPixelFormat()))


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
        raise RuntimeError('the 3D View panel is not visible in Designer')
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


def save_screenshot(panel, out_path):
    """Render one of Designer's own widgets to PNG with QWidget.grab(), or the 3D view via its
    own render. Screen/window grabs are deliberately not used: on macOS they copy whatever
    covers Designer, i.e. other apps."""
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
            raise RuntimeError('panel %r is not visible in Designer (open it via the Windows menu)' % panel)
        widget = docks[0]
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
    builders = {
        'bool': lambda: SDValueBool.sNew(bool(value)),
        'int': lambda: SDValueInt.sNew(int(value)),
        'float': lambda: SDValueFloat.sNew(float(value)),
        'string': lambda: SDValueString.sNew(str(value)),
        'float2': lambda: SDValueFloat2.sNew(float2(*map(float, seq))),
        'float3': lambda: SDValueFloat3.sNew(float3(*map(float, seq))),
        'float4': lambda: SDValueFloat4.sNew(float4(*map(float, seq))),
        'int2': lambda: SDValueInt2.sNew(int2(*map(int, seq))),
        'int3': lambda: SDValueInt3.sNew(int3(*map(int, seq))),
        'int4': lambda: SDValueInt4.sNew(int4(*map(int, seq))),
        'ColorRGBA': lambda: SDValueColorRGBA.sNew(ColorRGBA(*map(float, (seq + [1.0])[:4]))),
    }
    if tid not in builders:
        raise RuntimeError('%s: unsupported parameter type %s' % (prop.getId(), tid))
    if tid[-1].isdigit() and (seq is None or len(seq) != int(tid[-1])):
        raise RuntimeError('%s expects %s values' % (prop.getId(), tid[-1]))
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
        if pid.startswith('$') and hasattr(target, 'setPropertyInheritanceMethod'):
            # $outputsize/$format etc. only take effect when not inherited
            try:
                target.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
            except (Exception, APIException):
                pass
        target.setPropertyValue(prop, _make_value(prop, value))
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


def add_node(graph_id, definition, position=None, params=None):
    from sd.api.sdbasetypes import float2
    g = find_graph(graph_id)
    existing = list(g.getNodes())
    node = _resolve_definition(g, definition)
    if position is None:
        # to the right of everything, so it doesn't land on top of existing nodes
        xs = [n.getPosition().x for n in existing] or [0.0]
        ys = [n.getPosition().y for n in existing] or [0.0]
        position = (max(xs) + 200.0, sum(ys) / len(ys))
    node.setPosition(float2(float(position[0]), float(position[1])))
    print('added %s %s @(%d,%d)' % (node.getIdentifier(), node_kind(node), position[0], position[1]))
    print('outputs:', [p.getId() for p in node.getProperties(SDPropertyCategory.Output)])
    if params:
        set_params(graph_id, node.getIdentifier(), params)


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


# ---------------------------------------------------------------- editor / graphs
def _process_events(n=10):
    from PySide6 import QtWidgets
    for _ in range(n):
        QtWidgets.QApplication.instance().processEvents()


def open_graph(identifier, node_id=None):
    """Open a graph in Designer's graph editor; optionally centre the view on a node."""
    g = find_graph(identifier)
    ui = _APP.getUIMgr()
    ui.openResourceInEditor(g)
    _process_events()
    print('opened', g.getIdentifier())
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
    g = find_graph(None) if _APP.getQtForPythonUIMgr().getCurrentGraph() else None
    tmp = None
    if g is None:
        from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
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
