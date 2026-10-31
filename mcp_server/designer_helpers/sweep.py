"""sweep_param."""

from .core import (
    Any,
    SDNode,
    SDProperty,
    SDPropertyCategory,
    SDSBSCompGraph,
    SDTexture,
    SDValue,
    cast,
    find_graph,
    fmt,
    os,
)
from .describe import _with_node_texture
from .edits import _make_value, _node, _target
from .graph_inputs import _driving_graph


def sweep_param(
    identifier: str | SDSBSCompGraph | None,
    node_id: str | None,
    param: str,
    values: list[Any],
    out_dir: str,
    view_node: str | None = None,
    output: str | None = None,
) -> None:
    """Set `param` on `node_id` (or graph input when node_id == 'graph') to each value, dump the
    raw pixels of `view_node` (default: the same node) per value, then restore the original."""
    import ctypes
    import json

    g = find_graph(identifier)
    target = _target(g, node_id)
    prop = target.getPropertyFromId(param, SDPropertyCategory.Input)
    if prop is None or prop.isConnectable():
        raise RuntimeError('%r is not a parameter of %s; see describe_node / list_graph_inputs' % (param, node_id))
    if node_id != 'graph' and _driving_graph(cast(SDNode, target), prop) is not None:
        raise RuntimeError(
            '%s.%s is driven by a graph input or function; sweep the graph input '
            'instead (node_id="graph", param=<input id>, see list_graph_inputs)' % (node_id, param)
        )
    view = _node(g, view_node or node_id) if (view_node or node_id != 'graph') else None
    if view is None:
        raise RuntimeError('sweeping a graph input needs view_node (the node to look at)')
    original = cast(SDValue, target.getPropertyValue(prop))  # a parameter always has a value
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

            def use(texture: SDTexture, out_prop: SDProperty, i: int = i, value: Any = value) -> None:
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
        # the inheritance first: changing it resets the value to the default (REVIEW.md HLP-26)
        try:
            if inherit is not None:
                target.setPropertyInheritanceMethod(prop, inherit)
        finally:  # the value goes back even if putting the inheritance back fails
            target.setPropertyValue(prop, original)
        print('restored %s.%s to %r' % (node_id or 'graph', param, original_text))
