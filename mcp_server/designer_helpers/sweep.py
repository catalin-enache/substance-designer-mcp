"""sweep_param."""

from .core import (
    Json,
    SDNode,
    SDProperty,
    SDPropertyCategory,
    SDSBSCompGraph,
    SDTexture,
    _graph_to_edit,
    _value,
    cast,
    fmt,
    os,
)
from .describe import _with_node_texture
from .edits import _make_value, _node, _target
from .graph_inputs import (
    _REPLACE,
    _driving_graph,
    _offset_note,
    _plain_binding,
    _refuse_bad_size_on_input,
    _refuse_no_input,
    _refuse_no_output,
)


def sweep_param(
    identifier: str | SDSBSCompGraph | None,
    node_id: str | None,
    param: str,
    values: list[Json],  # checked by _make_value
    out_dir: str,
    view_node: str | None = None,
    output: str | None = None,
) -> None:
    """Set `param` on `node_id` (or graph input when node_id == 'graph') to each value, dump the
    raw pixels of `view_node` (default: the same node) per value, then restore the original."""
    import ctypes
    import json

    g = _graph_to_edit(identifier)
    target = _target(g, node_id)
    prop = target.getPropertyFromId(param, SDPropertyCategory.Input)
    if prop is None or prop.isConnectable():
        raise RuntimeError('%r is not a parameter of %s; see describe_node / list_graph_inputs' % (param, node_id))
    driven = _driving_graph(cast(SDNode, target), prop) if node_id != 'graph' else None
    if driven is not None:
        _refuse_no_output(driven, node_id, param)
        _refuse_no_input(g, driven, node_id, param)
        raise RuntimeError(
            '%s.%s is driven by a graph input or function; sweep the graph input '
            'instead (node_id="graph", param=<input id>, see list_graph_inputs)%s%s'
            % (
                node_id,
                param,
                _offset_note(target, prop),
                # a function, which set_function replaces (REVIEW.md HLP-230)
                '; or ' + _REPLACE if _plain_binding(driven) is None else '',
            )
        )
    _refuse_bad_size_on_input(target, prop, values)  # before any value is set
    view = _node(g, view_node or node_id) if (view_node or node_id != 'graph') else None
    if view is None:
        raise RuntimeError('sweeping a graph input needs view_node (the node to look at)')
    made = [_make_value(prop, value) for value in values]  # all of them before anything changes
    original = _value(target, prop)
    original_text = fmt(original)
    from sd.api.sdproperty import SDPropertyInheritanceMethod

    inherit: SDPropertyInheritanceMethod | None = None  # once read, put back
    put = [False]

    def put_back() -> None:
        """The parameter as it was: its inheritance first, as changing it resets the value to the default (REVIEW.md
        HLP-26), then its value, even if putting the inheritance back fails. Then says so: the server warns that the
        parameter may not be back without that line, which a sweep stopped by an error says too (REVIEW.md SRV-2,
        HLP-179). Run twice, it sets the same again, and says it again."""
        try:
            if inherit is not None:
                target.setPropertyInheritanceMethod(prop, inherit)
        finally:
            target.setPropertyValue(prop, original)
        print('restored %s.%s to %r' % (node_id or 'graph', param, original_text))
        put[0] = True

    try:  # from the inheritance's change on: an abort landing on a `try:` line isn't caught by its `finally`
        try:
            if param.startswith('$') and hasattr(target, 'getPropertyInheritanceMethod'):
                # like set_params: $outputsize/$format only take effect when not inherited
                inherit = target.getPropertyInheritanceMethod(prop)
                target.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)
            for i, (value, new_value) in enumerate(zip(values, made, strict=True)):
                target.setPropertyValue(prop, new_value)

                def use(texture: SDTexture, out_prop: SDProperty, i: int = i, value: Json = value) -> None:
                    size = texture.getSize()
                    pitch = texture.getRowPitch()
                    with open(os.path.join(out_dir, '%d.raw' % i), 'wb') as f:
                        f.write(ctypes.string_at(texture.getPixelBufferAddress(), pitch * size.y))
                    print(
                        'SWEEP='
                        + json.dumps(
                            {
                                'index': i,
                                'value': fmt(target.getPropertyValue(prop)),
                                'width': size.x,
                                'height': size.y,
                                'pitch': pitch,
                                'bpp': texture.getBytesPerPixel(),
                                'format': str(texture.getPixelFormat()).split('.')[-1],
                            }
                        )
                    )

                _with_node_texture(g, view, output, use)
        finally:
            put_back()
    except BaseException:
        # the plugin raises an abort at a traced line, then stops tracing: landed in the put-back, it skipped the rest
        # of it. Here, untraced, it is done again unless it was (REVIEW.md HLP-177)
        if not put[0]:
            put_back()
        raise
