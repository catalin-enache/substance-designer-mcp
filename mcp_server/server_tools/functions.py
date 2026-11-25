"""Function graphs: set_function, on a node's function or on a function graph stored in the package. A read in Designer
gives the target, the graph's inputs and the package's function graphs; the server compiles the expression
(function_compiler.py) and checks its type against the target; then one undo step builds it
(designer_helpers/functions.py)."""

import json
import re
from typing import Annotated, TypedDict

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from function_compiler import (
    DEFINITIONS,
    NUMBERS,
    ONLY_PROCESSORS,
    ExpressionError,
    Function,
    Kind,
    Resource,
    compile_expression,
    converted,
    image_input,
    joined_with,
    name_refusal,
    with_article,
)

from .core import Graph, _bridge, _checked, _edit, _helpers_call, _sentence, _tool

# What goes in set_function's expression: the grammar function_compiler.py compiles
EXPRESSION = """\
The function, in Python's expression syntax: statements `name = value`, each on a line of its own or after `;`, then \
the result. Example: `xy = $pos * 2 - 1; sqrt(max(0, 1 - dot(xy, xy)))`. A # not followed by a letter starts a comment.
Values: numbers, int or float as their use needs (alone, a float); true, false; the graph's inputs by id (a colour is \
a float4, an enum an int); the node's input values by #name, each a value connected into it (apply_edits' connect to \
input "#name"), such as a Value Processor's; a function graph's own inputs by id, in its own expression; Designer's \
variables $pos (float2: in a Pixel Processor's function and the function graphs it calls, the pixel's centre over \
the size, so 0 to 1, y from the top row; refused in a Value Processor's or a parameter's function, where it isn't \
the pixel's; a function graph reading it, called from those, isn't checked), $size (float2: the size in pixels), \
$sizelog2 (float2: its log2), $tiling (int) and $time (float). $depth and $number are an FX-Map's, refused.
float(), int(), float2() to float4() and int2() to int4(): a cast of one value, or components that add up, such as \
float4(xy, 0, 1). Swizzles: .x, .xy, .zyx, .rgba.
Operators: + - * / %, unary -, == != < <= > >=, and, or, not, `a if condition else b`. A float times a float vector \
scales it; in + - /, a float with a float vector acts on each component. Another mix of types is refused, the message \
naming the cast or swizzle to write. / of two ints truncates (int(7) / 2 is 3). Designer computes negative ints wrongly: \
keep ints at 0 or above, and use floats for signed values (a negative int number is refused).
Functions: abs, ceil, floor, sqrt, exp, log (natural), log2, sin, cos, tan (radians), min, max, pow, lerp(a, b, x), \
dot, rand(max) (from 0 to max; in a Pixel Processor's function, varying from pixel to pixel), cartesian(rho, \
theta), atan2(y, x), clamp(x, low, high), length, normalize; and the package's function graphs by identifier, such \
as paint(uv, 0.5), their arguments of their inputs' types, in order. A function graph can't call itself, directly \
or through others.
Sampling, in a Pixel or Value Processor's function and the function graphs it calls: sample(index, pos) reads the \
node's input image index (0 for input, 1 for input:1...) at pos, a float2 from (0, 0) at the top-left to (1, 1), as a \
float4; sample_lum(index, pos) gives its grey, the mean of R, G and B, a float. By name: filter='nearest' (the \
default) or 'bilinear', wrap='repeat' (the default) or 'clamp'. index is a whole number, 0 or more.
Every name and type is checked before anything is built, and a mistake names its column."""


class _Typed(TypedDict):
    """A parameter or a graph input as the read gives it: Designer's type id, and the get_* reading it in a function
    (designer_helpers' _GETTERS), None where none does."""

    type: str
    getter: str | None


class _End(TypedDict):
    """The other end of a value connection: its node and connector, as `node.connector`, and that connector's type."""

    end: str
    type: str


class _Resource(TypedDict):
    """A function graph of the package, as the read gives it: its inputs by id, in a call's order; its output's type,
    None without an output node of one type; the package's function graphs it calls; the indices of its caller's input
    images it samples."""

    inputs: dict[str, _Typed]
    output: str | None
    calls: list[str]
    samples: list[int]


class _Target(TypedDict):
    """What the read gives (function_target, designer_helpers/functions.py, which prints the same keys)."""

    graph: str  # the graph's identifier
    package: str  # its package's file, or for one never saved its UID
    node: str
    parameter: str
    kind: Kind  # a Pixel or Value Processor's own function, or a parameter's
    value: _Typed  # the parameter's
    colorswitch: bool | None  # a Pixel Processor's
    inputs: dict[str, _Typed]  # the graph's, by id, and the node's input values, by #name
    fed: dict[str, _End | None]  # what is connected into each input value, None for nothing
    drives: list[_End]  # the input values a Value Processor's output feeds, for its own function
    functions: dict[str, _Resource]  # the package's function graphs, by identifier
    # a processor's input images, input, input:1... up to the last one connected: whether each is; None for a parameter
    images: list[bool] | None


class _Reach(TypedDict):
    """A node's function calling a function graph, directly or through others: the node as graph/node, the parameter,
    and the node's input images as the read gives a processor's (_Target's images), None for a parameter's function."""

    where: str
    parameter: str
    images: list[bool] | None


class _ResourceTarget(TypedDict):
    """What the read gives of a function graph of the package (function_resource_target, designer_helpers/
    functions.py, which prints the same keys)."""

    graph: str  # the graph whose package holds it
    package: str
    function: str  # its identifier
    functions: dict[str, _Resource]  # the package's function graphs, by identifier, this one too once it exists
    callers: list[str]  # what calls it: function graphs by identifier, a node's function as graph/node.parameter
    fx_map_callers: list[str]  # an FX-Map's inner node's functions calling it, as graph/node/inner.parameter
    reaching: list[_Reach]  # each node's function calling it, directly or through others: what it samples reaches it


NOTHING = ' Nothing was built.'
# how set_function and describe_graph refuse a function named both ways, and a parameter given for a function graph
NODE_OR_FUNCTION = "Give node_id, for a node's function, or function, for a function graph of the package"
NO_PARAMETER = "parameter is a node's: a function graph has none."

# the results a Pixel Processor computes a value of: any other type computes black (GUIDE.md, Building a function graph)
PIXEL = ('float', 'float4')
# the results a Value Processor's function takes
VALUE = ('bool', *NUMBERS)
# how a Pixel Processor shows its result, by colorswitch and the result's type (GUIDE.md, Building a function graph;
# a colour image into a blend's opacity: Library node facts)
SHOWN = {
    (True, 'float'): 'colorswitch is on: the output is a colour image, the float in R, G and B. '
    "A blend's opacity reads a colour image as 0, so a mask needs colorswitch off.",
    (True, 'float4'): 'colorswitch is on: the float4 is the colour.',
    (False, 'float'): 'colorswitch is off: the float is the grayscale value.',
    (False, 'float4'): 'colorswitch is off: the float4 is averaged to grey (the mean of R, G and B, alpha left out).',
}


def _function_type(typed: _Typed) -> str:
    """The type a function gives or reads for a parameter or graph input: its getter's output, or else Designer's type
    id, which the compiler refuses to read."""
    getter = typed['getter']
    return DEFINITIONS[getter].output[0] if getter else typed['type']


def _read(call: str, key: str) -> str:
    """The JSON a read helper prints after `key=`."""
    text = _checked(_bridge(_helpers_call(call), timeout=60))
    found = re.search(r'^%s=(\{.*\})$' % key, text, re.M)
    if not found:
        raise ToolError(text.strip().splitlines()[-1] if text.strip() else 'no answer from Designer')
    return found.group(1)


def _read_target(graph: str | None, node_id: str | None, parameter: str | None) -> _Target:
    target: _Target = json.loads(_read('function_target(%r, %r, %r)' % (graph, node_id, parameter), 'FUNCTION_TARGET'))
    return target


def _types(inputs: dict[str, _Typed]) -> dict[str, str]:
    """Inputs as the compiler reads them: each by its function type (_function_type)."""
    return {name: _function_type(typed) for name, typed in inputs.items()}


def _callable(functions: dict[str, _Resource]) -> dict[str, Resource]:
    """The package's function graphs as the compiler calls them."""
    return {
        name: Resource(_types(r['inputs']), r['output'], tuple(r['calls']), tuple(r['samples']))
        for name, r in functions.items()
    }


def _refusal(target: _Target, result: str) -> str | None:
    """Why the target can't take a function giving `result`, or None when it can."""
    where = '%s.%s' % (target['node'], target['parameter'])
    if target['kind'] == 'perpixel':
        if result in PIXEL:
            return None
        fix = ': write float4(c, 1) for a colour c' if result == 'float3' else ''
        black = 'which a Pixel Processor computes as black. It takes a float or a float4'
        return '%s: the expression gives %s, %s%s.' % (where, with_article(result), black, fix)
    if target['kind'] == 'function':
        if result in VALUE:
            return None
        return (
            "%s: the expression gives %s, and a Value Processor's function takes a bool, an int to int4 or a float to "
            'float4.' % (where, with_article(result))
        )
    value = target['value']
    need = _function_type(value)
    if result == need:
        return None
    designer = ' (its type, %s, as a function gives it)' % value['type'] if value['type'] != need else ''
    # a colour's alpha only the writer knows, as for a Pixel Processor (REVIEW.md SRV-193)
    fix = 'float4(c, 1)' if (result, need) == ('float3', 'float4') else converted('c', result, need)
    hint = ': write %s for its result c' % fix if fix else ''
    return '%s takes %s%s, and the expression gives %s%s.' % (
        where,
        with_article(need),
        designer,
        with_article(result),
        hint,
    )


def _values_read(function: Function) -> list[str]:
    """The node's input values `function` reads: the #names its get_* nodes read."""
    gets = [n['constant'] for n in function['nodes'] if n['definition'].startswith('get_')]
    return sorted({c for c in gets if isinstance(c, str) and c.startswith('#')})


# what a refusal or a result line says to do about an input value with nothing connected
CONNECT = "connect a value into it first (apply_edits' connect to input %r)"


def _value_refusal(target: _Target, function: Function) -> str | None:
    """Why Designer would read an input value wrongly, raising nothing (GUIDE.md, Input values): one a parameter's
    function reads has nothing connected; one the function reads is fed another type; or the Value Processor's result
    has another type than one it drives. None when none would be."""
    node = target['node']
    for name in _values_read(function):
        source, own = target['fed'][name], target['inputs'][name]['type']
        if source is None and target['kind'] == 'parameter':
            return '%s.%s has nothing connected: %s.' % (node, name, CONNECT % name)
        if source is not None and source['type'] != own:
            return (
                '%s.%s is an input value of type %s, and %s, connected into it, gives %s, which Designer reads wrongly: '
                'connect that output into another #name.' % (node, name, own, source['end'], source['type'])
            )
    for driven in target['drives']:
        if driven['type'] != function['type']:
            other, value = driven['end'].split('.', 1)
            return (
                "%s's output drives %s, an input value of type %s, and the expression gives %s, which Designer would "
                'read wrongly there: give %s, or disconnect %s first (an apply_edits disconnect op on node %r, input %r).'
                % (
                    node,
                    driven['end'],
                    driven['type'],
                    with_article(function['type']),
                    with_article(driven['type']),
                    driven['end'],
                    other,
                    value,
                )
            )
    return None


def _unconnected(target: _Target, function: Function) -> list[str]:
    """A line for each input value a Pixel or Value Processor's function reads with nothing connected: a float one
    reads 0 there, the only type measured (GUIDE.md, Input values). A parameter's is refused (_value_refusal)."""
    return [
        '%s.%s has nothing connected: %s.'
        % (target['node'], name, 'it reads 0' if target['inputs'][name]['type'] == 'float' else CONNECT % name)
        for name in _values_read(function)
        if target['fed'][name] is None
    ]


def _unsampled(node: str, images: list[bool], samples: list[int]) -> list[str]:
    """A line for each input image of `node` sampled (`samples`) with nothing connected (`images`, as the read gives
    them): it reads (0, 0, 0, 0) until an image is connected into it, and into the inputs before it, as Designer lists
    each once the one before it is connected (GUIDE.md, Sampling an image, and A processor's input images)."""
    lines = []
    for index in samples:
        if index < len(images) and images[index]:
            continue
        order = ''
        if index > len(images):  # the inputs from the first not listed to the one before it
            first, last = image_input(len(images)), image_input(index - 1)
            order = ', and into %s before it, in order' % (first if first == last else '%s to %s' % (first, last))
        lines.append(
            '%s.%s has nothing connected: sampling it reads (0, 0, 0, 0) until an image is connected into it%s '
            "(apply_edits' connect)." % (node, image_input(index), order)
        )
    return lines


def _unsampled_by_callers(function: str, reaching: list[_Reach], samples: list[int]) -> list[str]:
    """The lines _unsampled gives for each node calling the function graph `function`, which samples `samples`, and one
    for each parameter's function calling it, which has no input images (REVIEW.md SRV-199)."""
    if not samples:
        return []
    lines = []
    for r in reaching:
        caller = '%s.%s' % (r['where'], r['parameter'])
        if r['images'] is None:
            lines.append(
                '%s calls %s, which samples an input image, and %s: give %s another function with set_function.'
                % (caller, function, ONLY_PROCESSORS, caller)
            )
            continue
        called = '%s is called from %s, and ' % (function, caller)
        lines += [called + line for line in _unsampled(r['where'], r['images'], samples)]
    return lines


def _resource_refusal(function: str, inputs: dict[str, str]) -> str | None:
    """Why no expression could call the function graph `function` with `inputs`, or None."""
    refusal = name_refusal(function, True)
    if refusal:
        return refusal
    for input_id, type_ in inputs.items():
        why = name_refusal(input_id, False)
        # what a Value Processor gives, as Designer's own function graphs use them
        if why is None and type_ not in VALUE:
            why = "%s is no type a function graph's input takes: give %s" % (type_, joined_with(VALUE, 'or'))
        if why:
            return 'input `%s`: %s' % (input_id, why)
    return None


def _set_resource(expression: str, function: str, inputs: dict[str, str] | None, graph: str | None) -> str:
    """set_function's `function`: the function graph `function` of the graph's package, made or replaced."""
    inputs = inputs or {}  # as a client may send {} for a field left out
    refusal = _resource_refusal(function, inputs)
    if refusal:
        raise ToolError(_sentence(refusal) + NOTHING)
    target: _ResourceTarget = json.loads(
        _read('function_resource_target(%r, %r)' % (graph, function), 'FUNCTION_RESOURCE')
    )
    resources = _callable(target['functions'])
    before = resources.get(function)
    kept = before.inputs if before else {}
    given = inputs or kept  # none given: the ones it has
    try:
        compiled = compile_expression(expression, given, resources, function, images=True)
    except ExpressionError as e:
        raise ToolError(_sentence(str(e)) + NOTHING) from e
    if compiled['type'] not in VALUE:
        raise ToolError(
            '%s: the expression gives %s, and a function graph gives a bool, an int to int4 or a float to float4.%s'
            % (function, with_article(compiled['type']), NOTHING)
        )
    # left out, None: the build leaves them as Designer has them, a colour read as a float4 too (REVIEW.md HLP-233)
    call = 'set_function_resource(%r, %r, %r, %r)' % (graph, target, list(inputs.items()) if inputs else None, compiled)
    lines = [_edit(call, 'Claude: set function graph ' + function).rstrip()]
    changed = before is not None and (list(given.items()) != list(kept.items()) or compiled['type'] != before.output)
    callers, fx_map_callers = target['callers'], target['fx_map_callers']
    if changed and callers:
        lines.append(
            "%s's inputs or output changed, and %s call%s it: give each its function again with set_function, as a "
            'call reads 0 for an input it lost, and gives the new output.'
            % (function, joined_with(callers, 'and'), 's' if len(callers) == 1 else '')
        )
    if changed and fx_map_callers:  # set_function can't reach an FX-Map's inner node (REVIEW.md HLP-239)
        lines.append(
            "%s's inputs or output changed, and %s, in an FX-Map, call%s it, which set_function can't reach: tell the "
            'user to give each its function again in Designer.'
            % (function, joined_with(fx_map_callers, 'and'), 's' if len(fx_map_callers) == 1 else '')
        )
    return '\n'.join(lines + _unsampled_by_callers(function, target['reaching'], compiled['samples']))


@_tool(read_only=False, destructive=True, idempotent=True, open_world=False)
def set_function(
    expression: Annotated[str, Field(description=EXPRESSION)],
    node_id: Annotated[
        str | None, Field(description='The node whose function is replaced. Give node_id or function.')
    ] = None,
    parameter: Annotated[
        str | None,
        Field(
            description="The node's parameter whose function is replaced (default: a Pixel Processor's perpixel, a "
            "Value Processor's function)."
        ),
    ] = None,
    function: Annotated[
        str | None,
        Field(
            description="A function graph of the graph's package, by identifier: made, or its nodes and inputs "
            'replaced, the graph kept, so that the functions calling it still find it. An expression calls it by '
            "this name, so it can't be one of the grammar's functions or casts."
        ),
    ] = None,
    inputs: Annotated[
        dict[str, str] | None,
        Field(
            description="The function graph's inputs, {id: type} in a call's order, such as {'uv': 'float2', 'k': "
            "'float'}: each a bool, int to int4 or float to float4. Its expression reads them by id. Left out or {}, "
            'the function graph keeps the inputs it has, and a new one gets none: to have one with none, make it under '
            'another identifier.'
        ),
    ] = None,
    graph: Graph = None,
) -> str:
    """Replace a node's function with an expression, compiled into Designer's function nodes: a Pixel Processor's
    perpixel, a Value Processor's function, or any parameter's (such as a levels' leveloutlow from graph inputs). One
    undo step. The result must be a float or a float4 for a Pixel Processor, as other types compute
    black; any number or bool for a Value Processor, whose output takes its type, and one that drives input values
    must give their type (give it its function before connecting it); the parameter's own type for a parameter. An
    input value read must have a value of its type connected: a parameter's function refuses one with nothing, and a
    processor's result says it has nothing (a float one reads 0). A sampled input image with nothing connected reads
    (0, 0, 0, 0): the result says so, of each node calling a function graph too. A `$` parameter but $randomseed
    is made Absolute, as apply_edits' set makes it: inherited, a function on $outputsize is an offset and one on
    $format is ignored. On $outputsize the function gives log2 of the size, and a
    constant above 13 is refused. Nothing is built
    when anything is wrong: a name, a type, the node or the parameter. The result says how many nodes were built and the
    output's type, and how a Pixel Processor's colorswitch shows it.

    With `function` instead of `node_id`, it makes or replaces a function graph stored in the package, which any
    expression of the package then calls by name: the result gives its identifier, inputs and output's type, and names
    what calls it when its inputs or output changed. If a function graph it replaces fails to take its new inputs,
    Designer's Undo takes that step back while it is the newest, and the error says so."""
    if bool(node_id) == bool(function):
        raise ToolError('%s%s.%s' % (NODE_OR_FUNCTION, ', not both' if node_id else '', NOTHING))
    if function:
        if parameter:
            raise ToolError(NO_PARAMETER + NOTHING)
        return _set_resource(expression, function, inputs, graph)
    if inputs:
        raise ToolError("inputs are a function graph's: a node's function reads its graph's inputs." + NOTHING)
    target = _read_target(graph, node_id, parameter)
    images = target['images']
    try:
        compiled = compile_expression(
            expression,
            _types(target['inputs']),
            _callable(target['functions']),
            images=images is not None,
            kind=target['kind'],
        )
    except ExpressionError as e:
        raise ToolError(_sentence(str(e)) + NOTHING) from e
    refusal = _refusal(target, compiled['type']) or _value_refusal(target, compiled)
    if refusal:
        raise ToolError(refusal + NOTHING)
    where = '%s.%s' % (target['node'], target['parameter'])
    lines = [_edit('set_function(%r, %r, %r)' % (graph, target, compiled), 'Claude: set function of ' + where).rstrip()]
    if target['kind'] == 'perpixel':
        lines.append(SHOWN[(bool(target['colorswitch']), compiled['type'])])
    elif target['kind'] == 'function':
        lines.append("The Value Processor's output is %s now." % with_article(compiled['type']))
    sampled = _unsampled(target['node'], images or [], compiled['samples'])
    return '\n'.join(lines + _unconnected(target, compiled) + sampled)
