"""describe_graph, describe_node (library graphs, slider ranges) and node textures (previews,
pixels)."""

from .core import (
    _APP,
    _PM,
    Any,
    APIException,
    Callable,
    SDApplicationPath,
    SDNode,
    SDPackage,
    SDProperty,
    SDPropertyCategory,
    SDResourceFolder,
    SDSBSCompGraph,
    SDTexture,
    SDType,
    SDTypeEnum,
    SDValueTexture,
    _default_output,
    _other_end,
    _output_note,
    cast,
    find_graph,
    fmt,
    node_kind,
    os,
)
from .edits import _node, atomic_definition_ids
from .graph_inputs import _driver_text, _driving_graph, _fx_map_functions, _has_output
from .layout import graph_objects_summary


def _output_tags_text(node: SDNode) -> str:
    """What names an output node and what it is for, as the add and set ops set them."""
    try:
        identifier: Any = node.getAnnotationPropertyValueFromId('identifier')  # SDValueStrings
        label: Any = node.getAnnotationPropertyValueFromId('label')
        tags: Any = node.getAnnotationPropertyValueFromId('usages')
        array = tags.get() if tags is not None else None  # an SDValueArray of SDValueUsage
        names = [array.getItem(i).get().getName() for i in range(array.getSize())] if array is not None else []
        text = ' identifier=%r' % (identifier.get() if identifier is not None else '')
        if label is not None and label.get():
            text += ' label=%r' % label.get()
        return text + ' usage=%s' % (','.join(names) or 'none')
    except (Exception, APIException):  # one node's annotations mustn't cost the whole description
        return ''


def describe_graph(
    identifier: str | SDSBSCompGraph | None = None,
    node_ids: list[str] | None = None,
    include_params: bool = False,
    limit: int = 400,
) -> None:
    g = find_graph(identifier)
    nodes = list(g.getNodes())
    print('graph %s: %d nodes' % (g.getIdentifier(), len(nodes)))
    try:
        # an SDValueInt2; a None fails into the except below
        size = g.getInputPropertyValueFromId('$outputsize').get()  # type: ignore[union-attr]
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
        wanted = {str(i) for i in node_ids}
        found = {n.getIdentifier() for n in nodes}
        unknown = [str(i) for i in node_ids if str(i) not in found]
        if unknown:  # said, not dropped silently (REVIEW.md HLP-47)
            print('not found: %s' % ', '.join(unknown))
        nodes = [n for n in nodes if n.getIdentifier() in wanted]
    for n in nodes[:limit]:
        pos = n.getPosition()
        line = '%s %s @(%d,%d)' % (n.getIdentifier(), node_kind(n), pos.x, pos.y)
        if node_kind(n) == 'output':
            line += _output_tags_text(n)
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
            for inner_id, prop, fg in _fx_map_functions(n):
                if _has_output(fg):
                    print('    FX-Map %s %s <- %s' % (inner_id, prop.getId(), _driver_text(g, fg)))
                else:
                    print(
                        '    FX-Map %s %s: a function with no output node, which drives nothing'
                        % (inner_id, prop.getId())
                    )
            for prop in n.getProperties(SDPropertyCategory.Input):
                if prop.isConnectable():
                    continue
                driven = _driving_graph(n, prop)
                if driven is not None and not _has_output(driven):
                    print(
                        '    %s = %r (its function has no output node and drives nothing)'
                        % (prop.getId(), fmt(n.getPropertyValue(prop)))
                    )
                    continue
                if driven is not None:
                    # the stored constant is hidden and unused while a function drives the value
                    print('    %s <- %s' % (prop.getId(), _driver_text(g, driven)))
                    continue
                cur = fmt(n.getPropertyValue(prop))
                default = fmt(prop.getDefaultValue())
                if cur != default and not (
                    prop.getId() in ('$outputsize', '$pixelsize') and cur in ((0, 0), (1.0, 1.0))
                ):
                    print('    %s = %r' % (prop.getId(), cur))
    if len(nodes) > limit:
        print('... %d more nodes (raise limit or filter node_ids)' % (len(nodes) - limit))


def _library_path(name: str) -> tuple[str, str]:
    """(package file, graph) of a library definition: '<file>[/<graph>]', in Designer's packages folder or a
    subfolder, the file with or without its .sbs, the graph with its groups ('hbao', 'hbao.sbs/hbao',
    'materials/pbr/bricks_001', 'constant_values/float/constant_float'). A definition comes from an agent, so
    a file outside that folder is refused; the graph is looked up inside the package, which can't leave it
    (measured: '../bevel', 'sbs://bevel.sbs', an absolute path all find nothing; REVIEW.md HLP-61)."""
    pkg_dir = os.path.join(_APP.getPath(SDApplicationPath.DefaultResourcesDir), 'packages')
    graph_id = ''
    if '.sbs/' in name:
        file_name, graph_id = name.split('.sbs/', 1)
        file_name += '.sbs'
    elif name.endswith('.sbs'):
        file_name = name
    else:  # the longest part naming a package (REVIEW.md HLP-60); none: what was looked for, for the refusal
        file_name = name + '.sbs'
        parts = name.split('/')
        for i in range(len(parts), 0, -1):
            candidate = '/'.join(parts[:i]) + '.sbs'
            if os.path.exists(os.path.join(pkg_dir, candidate)):
                file_name, graph_id = candidate, '/'.join(parts[i:])
                break
    path = os.path.normpath(os.path.join(pkg_dir, file_name))
    root = os.path.realpath(pkg_dir)
    try:
        inside = os.path.commonpath([root, os.path.realpath(path)]) == root
    except ValueError:  # another drive on Windows
        inside = False
    if not inside:
        raise RuntimeError('%r is neither an atomic node nor a library package (outside %s)' % (name, pkg_dir))
    return path, graph_id or os.path.splitext(os.path.basename(file_name))[0]


def _load_library(path: str) -> SDPackage:
    for p in _PM.getPackages():
        if os.path.normpath(p.getFilePath() or '') == os.path.normpath(path):
            return p
    return _PM.loadUserPackage(path)


def _library_graph(definition: str) -> Any:
    """The library graph a definition names, for newInstanceNode. findResourceFromUrl finds a group too, and
    newInstanceNode then says only NotSupported (measured; REVIEW.md HLP-63)."""
    path, graph_id = _library_path(definition)
    if not os.path.exists(path):
        raise RuntimeError('%r is neither an atomic node nor a library package (%s)' % (definition, path))
    res = _load_library(path).findResourceFromUrl(graph_id)
    if res is None:
        raise RuntimeError('graph %r not found in %s' % (graph_id, path))
    if isinstance(res, SDResourceFolder):
        raise RuntimeError('%r names a group of its package, not a graph' % definition)
    return res


def _slider_range(node: SDNode, prop_id: str) -> str:
    """'range a..b step c' from a library graph's input annotations ('' for atomic nodes,
    whose ranges the API doesn't expose)."""
    ref = node.getReferencedResource()
    if ref is None or prop_id.startswith('$'):
        return ''
    try:
        rprop = ref.getPropertyFromId(prop_id, SDPropertyCategory.Input)
        if rprop is None:
            return ''
        values: dict[str, Any] = {}
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


def _short_description(prop: SDProperty) -> str:
    import re

    try:
        desc = prop.getDescription() or ''
    except (Exception, APIException):
        return ''
    desc = re.sub(r'<[^>]+>', '', desc).strip()
    return (desc[:157] + '...') if len(desc) > 160 else desc


def describe_node(definition: str) -> None:
    """definition: atomic name ('levels' or 'sbs::compositing::levels') or library
    '<package file>[/<graph id>]' (e.g. 'tile_generator', 'hbao.sbs/hbao', 'materials/pbr/bricks_001')."""
    tmp = _PM.newUserPackage()
    try:
        g = SDSBSCompGraph.sNew(tmp)
        atomic_id = definition if definition.startswith('sbs::') else 'sbs::compositing::' + definition
        node = g.newNode(atomic_id) if atomic_id in atomic_definition_ids(g) else None
        if node is None:
            res = _library_graph(definition)
            node = cast(SDNode, g.newInstanceNode(res))  # the resource was found just above
            path, graph_id = _library_path(definition)
            print('library node %s (%s)' % (graph_id, os.path.basename(path)))
        else:
            print('atomic node %s' % atomic_id)
        print('output connector ids:', [p.getId() for p in node.getProperties(SDPropertyCategory.Output)])
        print('inputs:')
        for prop in node.getProperties(SDPropertyCategory.Input):
            ptype = cast(SDType, prop.getType())  # a parameter always has a type
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
                print(
                    '      enum: '
                    + ', '.join('%s=%s' % (e.getId(), fmt(e.getDefaultValue())) for e in ptype.getEnumerators())
                )
    finally:
        _PM.unloadUserPackage(tmp)


def _with_node_texture(
    g: SDSBSCompGraph, node: SDNode, output: str | None, use: Callable[[SDTexture, SDProperty], None]
) -> None:
    """Compute the graph and call use(texture, output_property) for one node output. Designer
    computes the nodes that feed an output node and may skip others (AGENTS.md), so a temporary
    output node is attached when needed and removed afterwards."""
    outs = list(node.getProperties(SDPropertyCategory.Output))
    if output:
        outs = [p for p in outs if p.getId() == output]
    if not outs:
        raise RuntimeError(
            'output %r not found; outputs: %s'
            % (output, [p.getId() for p in node.getProperties(SDPropertyCategory.Output)])
        )
    if not output and len(outs) > 1:
        chosen, how = _default_output(node, [p.getId() for p in outs])
        print(_output_note(how))
        outs = [p for p in outs if p.getId() == chosen]
    g.compute()
    value = cast(SDValueTexture | None, node.getPropertyValue(outs[0]))
    texture = value.get() if value is not None else None
    temp_output = None
    try:
        if texture is None:
            temp_output = g.newNode('sbs::compositing::output')
            node.newPropertyConnectionFromId(outs[0].getId(), temp_output, 'inputNodeOutput')
            g.compute()
            value = cast(SDValueTexture | None, node.getPropertyValue(outs[0]))
            texture = value.get() if value is not None else None
        if texture is None:
            raise RuntimeError('node %s produced no texture (are its inputs connected?)' % node.getIdentifier())
        return use(texture, outs[0])
    finally:
        if temp_output is not None:
            g.deleteNode(temp_output)


def save_node_output(
    node_id: str, out_path: str, identifier: str | SDSBSCompGraph | None = None, output: str | None = None
) -> None:
    g = find_graph(identifier)
    node = _node(g, node_id)

    def use(texture: SDTexture, prop: SDProperty) -> None:
        texture.save(out_path)
        size = texture.getSize()
        print('%s %s.%s %dx%d %s' % (node_id, node_kind(node), prop.getId(), size.x, size.y, texture.getPixelFormat()))

    _with_node_texture(g, node, output, use)


def dump_node_pixels(
    node_id: str, out_path: str, identifier: str | SDSBSCompGraph | None = None, output: str | None = None
) -> None:
    """Write the node's raw pixel buffer to out_path and print its layout as JSON (for node_stats)."""
    import ctypes
    import json

    g = find_graph(identifier)
    node = _node(g, node_id)

    def use(texture: SDTexture, prop: SDProperty) -> None:
        size = texture.getSize()
        pitch = texture.getRowPitch()
        with open(out_path, 'wb') as f:
            f.write(ctypes.string_at(texture.getPixelBufferAddress(), pitch * size.y))
        print(
            'PIXELS='
            + json.dumps(
                {
                    'width': size.x,
                    'height': size.y,
                    'pitch': pitch,
                    'bpp': texture.getBytesPerPixel(),
                    'format': str(texture.getPixelFormat()).split('.')[-1],
                    'node': '%s %s.%s' % (node_id, node_kind(node), prop.getId()),
                }
            )
        )

    _with_node_texture(g, node, output, use)
