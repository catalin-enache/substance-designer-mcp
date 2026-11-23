"""describe_graph (a graph; a function's nodes: describe_functions.py), describe_node (library graphs, slider ranges,
function nodes) and node textures (previews, pixels)."""

from .core import (
    _APP,
    _MORE_HINT,
    _PM,
    APIException,
    Callable,
    SDApplicationPath,
    SDNode,
    SDPackage,
    SDProperty,
    SDPropertyCategory,
    SDResource,
    SDResourceFolder,
    SDSBSCompGraph,
    SDTexture,
    SDTypeEnum,
    SDValueArray,
    Shown,
    _annotation_text,
    _current_graph,
    _default_output,
    _focused,
    _function_definitions,
    _FunctionDefinition,
    _links_text,
    _more,
    _new_instance,
    _new_node,
    _node_head,
    _nodes,
    _output_note,
    _texture,
    _type,
    _type_ids,
    _ui,
    _usage_names,
    cast,
    find_graph,
    fmt,
    html,
    node_kind,
    os,
    re,
)
from .describe_functions import _function_graphs_line
from .edits import _node, atomic_definition_ids
from .graph_inputs import _driver_text, _driving_graph, _fx_map_functions, _has_output
from .layout import graph_objects_summary


def _output_tags_text(node: SDNode) -> str:
    """What names an output node and what it is for, as the add and set ops set them."""
    try:
        identifier = _annotation_text(node, 'identifier')
        label = _annotation_text(node, 'label')
        # a usage that reads as None fails into the except below
        names = _usage_names(node.getAnnotationPropertyValueFromId('usages'))
        text = ' identifier=%r' % (identifier or '')
        if label:
            text += ' label=%r' % label
        return text + ' usage=%s' % (','.join(names) or 'none')
    except (Exception, APIException):  # one node's annotations mustn't cost the whole description
        return ''


KEYS_SHOWN = 16  # the most keys a whole graph's listing shows of a parameter; node_ids, set's result and fmt give all


def describe_graph(
    identifier: str | SDSBSCompGraph | None = None,
    node_ids: list[str] | None = None,
    include_params: bool = False,
    limit: int = 400,
    hint: str = _MORE_HINT,
) -> None:
    """Lists a graph's nodes, and its package's function graphs (a function's nodes: describe_function). `hint` is
    what the line past `limit` says to do."""
    from sd.api.sdvalueint2 import SDValueInt2

    g = find_graph(identifier)
    nodes = _nodes(g)
    print('graph %s: %d nodes' % (g.getIdentifier(), len(nodes)))
    try:
        # a None fails into the except below
        size = cast(SDValueInt2 | None, g.getInputPropertyValueFromId('$outputsize')).get()  # type: ignore[union-attr]
        print('$outputsize (log2): %d x %d' % (size.x, size.y))
    except (Exception, APIException):
        pass
    try:
        frames, comments = graph_objects_summary(g)
        if frames or comments:
            print('frames: %s | comments: %d' % (', '.join(repr(f) for f in frames) or '-', comments))
    except (Exception, APIException):
        pass
    if not node_ids:  # focused on node_ids, a description leaves them out (REVIEW.md HLP-242)
        try:
            listed = _function_graphs_line(g.getPackage())
        except (Exception, APIException) as e:  # said, as a package with none says nothing
            listed = 'function graphs of the package: not read (%s)' % e
        if listed:
            print(listed)
    nodes = _focused(nodes, node_ids)
    for n in nodes[:limit]:
        line = _node_head(n)
        if node_kind(n) == 'output':
            line += _output_tags_text(n)
        print(line + _links_text(n))
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
                value = n.getPropertyValue(prop)
                default: Shown
                if isinstance(value, SDValueArray):
                    # keys have no default (None, measured): a new node has none. A long list shows as its count in a
                    # whole graph's listing; focused on its node, every key
                    count = value.getSize()
                    cur, default = fmt(value) if count <= KEYS_SHOWN or node_ids else '<%d keys>' % count, ()
                else:
                    cur, default = fmt(value), fmt(prop.getDefaultValue())
                if cur != default and not (
                    prop.getId() in ('$outputsize', '$pixelsize') and cur in ((0, 0), (1.0, 1.0))
                ):
                    print('    %s = %r' % (prop.getId(), cur))
    _more(nodes, limit, hint)


def describe_selected(identifier: str | None = None, include_params: bool = False, limit: int = 400) -> None:
    """describe_graph(selected=True): the graph in the editor, only its nodes selected there (describe_graph's
    node_ids), then a line naming the frames, comments and pins selected too. A graph given must be the one in the
    editor. The getters read the graph in the editor, and raise once no graph view is left there, so the graph is
    checked first (GUIDE.md, Designer UI)."""
    from sd.api.sdgraphobjectcomment import SDGraphObjectComment
    from sd.api.sdgraphobjectframe import SDGraphObjectFrame
    from sd.api.sdgraphobjectpin import SDGraphObjectPin

    g = _current_graph()
    if g is None:
        raise RuntimeError("No graph is open in Designer's editor, so nothing is selected there.")
    if not isinstance(g, SDSBSCompGraph):
        raise RuntimeError(
            "The graph open in Designer's editor (%s) is not a compositing graph: selected reads a compositing graph's "
            'selection only.' % g.getIdentifier()
        )
    if identifier and identifier != g.getIdentifier():
        raise RuntimeError(
            "selected reads the selection of the graph in Designer's editor, which is %r, not %r. To read one in %r, "
            'open it there with open_graph and have the user select in it.'
            % (g.getIdentifier(), identifier, identifier)
        )
    ui = _ui()
    node_ids = [n.getIdentifier() for n in ui.getCurrentGraphSelectedNodes() or []]
    objects = list(ui.getCurrentGraphSelectedObjects() or [])
    named = ['frame %r' % o.getTitle() for o in objects if isinstance(o, SDGraphObjectFrame)]
    for label, kind in (('comment', SDGraphObjectComment), ('pin', SDGraphObjectPin)):
        count = sum(isinstance(o, kind) for o in objects)
        if count:
            named.append('%d %s%s' % (count, label, 's' if count > 1 else ''))
    if not node_ids:  # describe_graph lists every node for no node_ids
        if named:
            print('graph %s: no node selected in the editor, only %s' % (g.getIdentifier(), ', '.join(named)))
        else:
            print('graph %s: nothing selected in the editor' % g.getIdentifier())
        return
    describe_graph(g, node_ids, include_params, limit, hint='raise limit')  # selected refuses node_ids (HLP-254)
    if named:
        print('also selected: ' + ', '.join(named))


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


def _library_graph(definition: str) -> SDResource:
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
        values: dict[str, Shown] = {}
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
    try:
        desc = prop.getDescription() or ''
    except (Exception, APIException):
        return ''
    desc = html.unescape(re.sub(r'<[^>]+>', '', desc)).strip()  # its entities after its tags (REVIEW.md HLP-246)
    return (desc[:157] + '...') if len(desc) > 160 else desc


def describe_node(definition: str) -> None:
    """definition: atomic name ('levels' or 'sbs::compositing::levels'), library
    '<package file>[/<graph id>]' (e.g. 'tile_generator', 'hbao.sbs/hbao', 'materials/pbr/bricks_001') or a function
    node's definition ('sbs::function::add': _describe_function_node). A name that is neither an atomic node nor a
    library package, but a function node's kind as a function's listing gives it ('add'), is that function node. One
    that is both ('pow', 'passthrough') is the other node, and a last line names the function node."""
    if definition.startswith('sbs::function::'):
        found = _function_definitions().get(definition)
        if found is None:
            raise RuntimeError('%r is no function node; search_nodes lists them' % definition)
        _describe_function_node(found)
        return
    before = _package_uids()
    try:
        try:
            tmp = _PM.newUserPackage()
            g = SDSBSCompGraph.sNew(tmp)
            atomic_id = definition if definition.startswith('sbs::') else 'sbs::compositing::' + definition
            node = _new_node(g, atomic_id) if atomic_id in atomic_definition_ids(g) else None
            # a kind as a function's listing gives it (REVIEW.md SRV-204); an id of another module is no key
            function = 'sbs::function::' + definition
            twin = _function_definitions().get(function)
            if node is None:
                path, graph_id = _library_path(definition)
                if twin is not None and not os.path.exists(path):
                    _describe_function_node(twin)
                    return
                node = _new_instance(g, _library_graph(definition))  # _library_graph raises if it finds none
                print('library node %s (%s)' % (graph_id, os.path.basename(path)))
            else:
                print('atomic node %s' % atomic_id)
            print('output connector ids:', [p.getId() for p in node.getProperties(SDPropertyCategory.Output)])
            print('inputs:')
            for prop in node.getProperties(SDPropertyCategory.Input):
                ptype = _type(prop)
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
            if twin is not None:  # pow, a library graph, passthrough, an atomic node (REVIEW.md SRV-205)
                print("%s is a function node's kind too: describe_node(%r) describes that one" % (definition, function))
        finally:
            _unload_new_packages(before)
    except BaseException:
        # the plugin raises an abort at a traced line, then stops tracing: landed on the unload, it skipped it, and one
        # landing as the package was made left no name for it. Here, untraced, they are unloaded unless they were
        # (REVIEW.md HLP-177)
        _unload_new_packages(before)
        raise


def _describe_function_node(found: _FunctionDefinition) -> None:
    """describe_node of a function node, read from its definition in Designer's sbs::function module: its label and
    description, then its output and its inputs, each with every type it takes (getTypes(): getType() gives only the
    first; GUIDE.md, Building a function graph), an input's label, and a constant's default."""
    description = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', found.description)).split())  # REVIEW.md HLP-246
    shown = ': ' + description if description else ''
    print('function node %s "%s"%s' % (found.sd_definition.getId(), found.label, shown))
    print('outputs:')  # an output's label is the node's
    for prop in found.sd_definition.getProperties(SDPropertyCategory.Output) or []:
        print('  %-28s %s' % (prop.getId(), ','.join(_type_ids(prop)) or 'none'))
    print('inputs:')
    for prop in found.sd_definition.getProperties(SDPropertyCategory.Input) or []:
        types = ','.join(_type_ids(prop)) or 'none'
        line = '  %-28s %s' % (prop.getId(), ('CONNECTOR ' if prop.isConnectable() else '') + types)
        if prop.getLabel():
            line += ' "%s"' % prop.getLabel()
        if not prop.isConnectable():
            line += ' default=%r' % (fmt(prop.getDefaultValue()),)
        print(line)


def _with_node_texture(
    g: SDSBSCompGraph, node: SDNode, output: str | None, use: Callable[[SDTexture, SDProperty], None]
) -> None:
    """Compute the graph and call use(texture, output_property) for one node output. Designer
    computes the nodes that feed an output node and may skip others (GUIDE.md), so a temporary
    output node is attached when needed and removed afterwards. With the graph open in the editor and an output node
    in it, the first compute after attaching sometimes gave no texture right after another node was measured this way,
    and the next compute gave it (9 times in 9): so a second compute, only then (REVIEW.md HLP-100). That came from the
    plugin starting the job at once after the one before; it now waits first (REVIEW.md PLG-38), and the second compute
    stays as a defence."""
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
    texture = _texture(node, outs[0])
    if texture is not None:
        use(texture, outs[0])
        return
    before = {n.getIdentifier() for n in _nodes(g)}
    try:
        try:
            temp_output = _new_node(g, 'sbs::compositing::output')
            node.newPropertyConnectionFromId(outs[0].getId(), temp_output, 'inputNodeOutput')
            for _ in range(2):  # the second only when the first gave none (the docstring)
                g.compute()
                texture = _texture(node, outs[0])
                if texture is not None:
                    break
            if texture is None:
                raise RuntimeError('node %s produced no texture (are its inputs connected?)' % node.getIdentifier())
            use(texture, outs[0])
        finally:
            _delete_new_nodes(g, before)
    except BaseException:
        # the plugin raises an abort at a traced line, then stops tracing: landed on the deletion, it skipped it, and
        # one landing as the node was added left no name for it. Here, untraced, it is deleted unless it was (REVIEW.md
        # HLP-177)
        _delete_new_nodes(g, before)
        raise


def _delete_new_nodes(g: SDSBSCompGraph, before: set[str]) -> None:
    """Deletes the nodes of `g` whose identifier isn't in `before`: the ones a call added. Listed again each time, so a
    second run deletes none twice."""
    for n in _nodes(g):
        if n.getIdentifier() not in before:
            g.deleteNode(n)


def _package_uids() -> set[str]:
    """The UIDs of the user packages loaded now, for _unload_new_packages."""
    return {p.getUID() for p in _PM.getUserPackages()}


def _unload_new_packages(before: set[str]) -> None:
    """Unloads the user packages with no file whose UID isn't in `before` (_package_uids): the ones a call made. A
    package made through the API has a UID of its own and no file, and a library package loaded meanwhile has its file
    (designer facts: discovery's checks). Listed again each time, so a second run unloads none twice: unloading a
    package twice crashed Designer (measured 2026-11-16, SIGSEGV in its UnreferencePackageCommand; not checked again,
    as the check would crash its Designer)."""
    for package in list(_PM.getUserPackages()):
        if package.getUID() not in before and not package.getFilePath():
            _PM.unloadUserPackage(package)


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
